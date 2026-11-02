"""Small local evaluation: automated structure checks plus explicit human review."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter

import httpx
from app.services.chunking import chunk_text
from app.services.ollama import embed_texts
from app.services.retrieval import search_chunks
from app.services.generation import answer_with_sources

ROOT = Path(__file__).resolve().parents[2]


def evidence_coverage(quotes, results):
    """Exact-quote coverage, not semantic relevance or answer correctness."""
    if not quotes:
        return None
    return sum(any(quote in item["text"] for item in results) for quote in quotes) / len(quotes)


async def evaluate_case(case, chunks, top_k):
    start = perf_counter()
    row = {"id": case["id"], "question": case["question"],
           "language": case["language"], "expected_found": case["expected_found"],
           "expected_answer": case["expected_answer"], "evidence_quotes": case["evidence_quotes"],
           "retrieved": [], "output": None, "error": None,
           "schema_and_ids_valid": False, "found_matches_expected": None,
           "exact_quote_coverage": None,
           "manual_review": {"answer_correct": None, "conditions_complete": None,
                             "citations_support_claims": None, "language_correct": None, "notes": ""}}
    try:
        query = (await embed_texts([case["question"]]))[0]
        results = search_chunks(query, chunks, top_k=top_k)
        row["retrieved"] = results
        row["exact_quote_coverage"] = evidence_coverage(case["evidence_quotes"], results)
        answer = await answer_with_sources(case["question"], results)
        row["output"] = answer.model_dump()
        row["schema_and_ids_valid"] = True
        row["found_matches_expected"] = answer.found == case["expected_found"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        row["error"] = {"type": type(error).__name__, "message": str(error)}
    row["latency_seconds"] = round(perf_counter() - start, 3)
    return row


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    dataset_path = ROOT / "samples/evaluation.json"
    dataset = json.loads(dataset_path.read_text())
    handbook = ROOT / "samples/company-handbook.md"
    document = handbook.read_text(encoding="utf-8")
    for case in dataset["cases"]:
        for quote in case["evidence_quotes"]:
            if quote not in document:
                raise ValueError(f"Missing gold evidence in document: {case['id']}")
    texts = chunk_text(document, chunk_size=250, overlap=50)
    if not texts:
        raise ValueError("Empty handbook")
    vectors = await embed_texts(texts)
    chunks = [{"id": f"chunk-{i}", "text": text, "source": handbook.name, "embedding": vector}
              for i, (text, vector) in enumerate(zip(texts, vectors), 1)]
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        response = await client.get("http://127.0.0.1:11434/api/tags")
        response.raise_for_status()
        installed = response.json()["models"]
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
              "dataset_version": dataset["version"],
              "config": {"chunk_size": 250, "overlap": 50, "top_k": args.top_k,
                         "chunk_count": len(chunks), "embedding_dimensions": len(vectors[0]),
                         "chat_model": "qwen2.5:3b", "embedding_model": "embeddinggemma"},
              "fingerprints": {str(p.relative_to(ROOT)): fingerprint(p) for p in
                               [dataset_path, handbook, ROOT / "backend/app/services/generation.py",
                                ROOT / "backend/app/schemas.py", ROOT / "backend/app/services/ollama.py"]},
              "installed_models": [{"name": m["name"], "digest": m.get("digest")} for m in installed],
              "results": []}
    output = args.output or ROOT / "reports" / (datetime.now(timezone.utc).strftime("rag-evaluation-%Y%m%dT%H%M%S%fZ.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    for case in dataset["cases"]:
        result = await evaluate_case(case, chunks, args.top_k)
        report["results"].append(result)
        # Save partial progress if a later model call or the process fails.
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"{case['id']}: schema={result['schema_and_ids_valid']} "
              f"found_match={result['found_matches_expected']} error={result['error']}", flush=True)
    rows = report["results"]
    report["summary"] = {"cases": len(rows), "errors": sum(row["error"] is not None for row in rows),
                         "schema_valid": sum(row["schema_and_ids_valid"] for row in rows),
                         "found_matches": sum(row["found_matches_expected"] is True for row in rows),
                         "human_review_required": True}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Report: {output}")
    print("Answer correctness, citation support and language require human review.")


if __name__ == "__main__":
    asyncio.run(main())
