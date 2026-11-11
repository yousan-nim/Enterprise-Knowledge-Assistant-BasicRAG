"""Evaluate handbook-v1 without changing the application database."""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config.config import EMBED_MODEL, OLLAMA_BASE_URL
from app.services.chunking import chunk_text
from app.services.generation import answer_with_sources
from app.services.ollama import embed_texts
from app.services.retrieval import search_chunks


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset(path: Path) -> tuple[dict, Path, str]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    document_path = ROOT / dataset["document_path"]
    document = document_path.read_text(encoding="utf-8").strip()

    if not document:
        raise ValueError("The evaluation document is empty.")

    cases = dataset["cases"]

    if not cases:
        raise ValueError("The dataset has no cases.")

    ids = set()

    for case in cases:
        case_id = case["id"]

        if case_id in ids:
            raise ValueError(f"Duplicate case ID: {case_id}")

        ids.add(case_id)

        if not case["question"].strip():
            raise ValueError(f"{case_id}: question is empty.")

        if type(case["answerable"]) is not bool:
            raise ValueError(f"{case_id}: answerable must be boolean.")

        evidence = case["expected_evidence"]

        if case["answerable"] != bool(evidence):
            raise ValueError(
                f"{case_id}: answerability and evidence disagree."
            )

        for item in evidence:
            # This starter runner supports a single Markdown page.
            if item["page"] != 1:
                raise ValueError(
                    f"{case_id}: this runner supports Markdown page 1 only."
                )

            if not item["text"] or item["text"] not in document:
                raise ValueError(
                    f"{case_id}: evidence quote is missing from the document."
                )

    return dataset, document_path, document


async def prepare_chunks(
    document: str,
    source: str,
    chunk_size: int,
    overlap: int,
) -> tuple[list[dict], float]:
    start = perf_counter()

    texts = chunk_text(
        document,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    vectors = await embed_texts(texts)
    step = chunk_size - overlap

    chunks = [
        {
            "id": f"chunk-{index + 1}",
            "text": text,
            "source": source,
            "page": 1,
            "extraction_method": "direct",
            "embedding": vector,
            "start": index * step,
            "end": index * step + len(text),
        }
        for index, (text, vector) in enumerate(zip(texts, vectors))
    ]

    return chunks, round(perf_counter() - start, 4)


def evidence_coverage(
    expected_evidence: list[dict],
    retrieved: list[dict],
    chunks: list[dict],
    document: str,
) -> float | None:
    """Fraction of gold quotes fully covered by retrieved chunk spans.

    A quote may span multiple chunks. This checks source-character coverage,
    not answer correctness or semantic support.
    """
    if not expected_evidence:
        return None

    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    spans = [
        chunk_by_id[result["id"]]
        for result in retrieved
    ]

    covered_quotes = 0

    for evidence in expected_evidence:
        quote = evidence["text"]
        position = document.find(quote)
        quote_is_covered = False

        # Accept any occurrence if the same quote appears more than once.
        while position >= 0:
            end = position + len(quote)

            if all(
                any(
                    chunk["page"] == evidence["page"]
                    and chunk["start"] <= offset < chunk["end"]
                    for chunk in spans
                )
                for offset in range(position, end)
            ):
                quote_is_covered = True
                break

            position = document.find(quote, position + 1)

        covered_quotes += int(quote_is_covered)

    return covered_quotes / len(expected_evidence)


async def evaluate_case(
    case: dict,
    chunks: list[dict],
    document: str,
    top_k: int,
) -> dict:
    total_start = perf_counter()

    row = {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expected_answerable": case["answerable"],
        "reference_answer": case["reference_answer"],
        "required_facts": case["required_facts"],
        "expected_evidence": case["expected_evidence"],
        "retrieved": [],
        "output": None,
        "error": None,
        "metrics": {
            "schema_and_ids_valid": False,
            "found_matches_expected": None,
            "gold_quote_coverage": None,
        },
        "timing_seconds": {},
        "manual_review": {
            "answer_correct": None,
            "required_facts_complete": None,
            "citations_support_claims": None,
            "language_correct": None,
            "notes": "",
        },
    }

    stage = "query_embedding"
    stage_start = perf_counter()

    try:
        query_vector = (await embed_texts([case["question"]]))[0]
        row["timing_seconds"][stage] = round(
            perf_counter() - stage_start, 4
        )

        stage = "retrieval"
        stage_start = perf_counter()

        results = search_chunks(
            query_vector,
            chunks,
            top_k=top_k,
        )

        row["timing_seconds"][stage] = round(
            perf_counter() - stage_start, 4
        )
        row["retrieved"] = results

        row["metrics"]["gold_quote_coverage"] = evidence_coverage(
            case["expected_evidence"],
            results,
            chunks,
            document,
        )

        stage = "generation_and_validation"
        stage_start = perf_counter()

        answer = await answer_with_sources(
            case["question"],
            results,
        )

        row["timing_seconds"][stage] = round(
            perf_counter() - stage_start, 4
        )

        row["output"] = answer.model_dump()
        row["metrics"]["schema_and_ids_valid"] = True
        row["metrics"]["found_matches_expected"] = (
            answer.found == case["answerable"]
        )

    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as error:
        row["timing_seconds"].setdefault(
            stage,
            round(perf_counter() - stage_start, 4),
        )
        row["error"] = {
            "stage": stage,
            "type": type(error).__name__,
            "message": str(error),
        }

    row["timing_seconds"]["total"] = round(
        perf_counter() - total_start, 4
    )

    return row


def summarize(rows: list[dict]) -> dict:
    evidence_scores = [
        row["metrics"]["gold_quote_coverage"]
        for row in rows
        if row["metrics"]["gold_quote_coverage"] is not None
    ]

    return {
        "completed_cases": len(rows),
        "errors": sum(row["error"] is not None for row in rows),
        "schema_and_ids_valid": sum(
            row["metrics"]["schema_and_ids_valid"] for row in rows
        ),
        "found_matches_expected": sum(
            row["metrics"]["found_matches_expected"] is True
            for row in rows
        ),
        "retrieval_scored_cases": len(evidence_scores),
        "mean_gold_quote_coverage": (
            round(sum(evidence_scores) / len(evidence_scores), 4)
            if evidence_scores
            else None
        ),
        "mean_total_seconds": (
            round(
                sum(row["timing_seconds"]["total"] for row in rows)
                / len(rows),
                4,
            )
            if rows
            else None
        ),
        "human_review_required": True,
    }


def save_report(path: Path, report: dict) -> None:
    # Write a temporary file first to preserve the previous partial report.
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "evaluation/datasets/handbook.json",
    )
    parser.add_argument("--chunk-size", type=int, default=250)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()

    if args.chunk_size <= 0:
        parser.error("--chunk-size must be positive.")

    if not 0 <= args.overlap < args.chunk_size:
        parser.error("--overlap must be between 0 and chunk-size - 1.")

    if not 1 <= args.top_k <= 10:
        parser.error("--top-k must be between 1 and 10.")

    dataset_path = args.dataset.resolve()
    dataset, document_path, document = load_dataset(dataset_path)

    now = datetime.now(timezone.utc)
    output = args.output or (
        ROOT
        / "reports"
        / now.strftime("handbook-evaluation-%Y%m%dT%H%M%S%fZ.json")
    )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Reserve the output name without overwriting an existing report.
    with output.open("x", encoding="utf-8") as file:
        file.write("{}\n")

    report = {
        "created_at": now.isoformat(),
        "dataset_id": dataset["dataset_id"],
        "status": "preparing",
        "scope": "in-memory retrieval; no API or pgvector evaluation",
        "config": {
            "chunk_size": args.chunk_size,
            "overlap": args.overlap,
            "top_k": args.top_k,
            "embedding_model": EMBED_MODEL,
            "chat_model": "qwen2.5:3b",
        },
        "fingerprints": {
            "dataset": fingerprint(dataset_path),
            "document": fingerprint(document_path),
        },
        "installed_models": [],
        "results": [],
        "summary": {},
    }
    save_report(output, report)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()

            report["installed_models"] = [
                {
                    "name": model["name"],
                    "digest": model.get("digest"),
                }
                for model in response.json()["models"]
            ]

        chunks, ingestion_seconds = await prepare_chunks(
            document,
            document_path.name,
            args.chunk_size,
            args.overlap,
        )

        report["config"]["chunk_count"] = len(chunks)
        report["config"]["embedding_dimensions"] = len(
            chunks[0]["embedding"]
        )
        report["ingestion_seconds"] = ingestion_seconds
        report["status"] = "running"
        save_report(output, report)

        for case in dataset["cases"]:
            row = await evaluate_case(
                case,
                chunks,
                document,
                args.top_k,
            )
            report["results"].append(row)
            report["summary"] = summarize(report["results"])
            save_report(output, report)

            print(
                f"{row['id']} | "
                f"found_match={row['metrics']['found_matches_expected']} | "
                f"evidence={row['metrics']['gold_quote_coverage']} | "
                f"time={row['timing_seconds']['total']}s | "
                f"error={row['error'] is not None}",
                flush=True,
            )

        report["status"] = (
            "completed_with_errors"
            if report["summary"]["errors"]
            else "completed"
        )

    except Exception as error:
        report["status"] = "failed"
        report["fatal_error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
        raise

    finally:
        save_report(output, report)
        print(f"\nReport: {output}", flush=True)

    print(
        "Answer correctness and citation support require human review."
    )

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))