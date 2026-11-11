# Handbook evaluation baseline

Fictional learning fixtures for Basic RAG evaluation. No production or personal data.

- `documents/handbook.md`: English source document; treat Markdown as page 1.
- `datasets/handbook.json`: four Thai questions covering direct retrieval, multiple evidence passages,
  an unanswerable question, and paraphrasing. The Thai questions also exercise cross-language retrieval.
- Paths in the dataset are relative to the repository root.

`reference_answer` is a human-review reference, not an exact string-match requirement.
`required_facts` lists claims to check manually. `expected_evidence` stores original quotes and page
numbers rather than unstable chunk IDs. A passage may span multiple chunks: evaluate combined retrieved
evidence as well as individual chunks. Correct citation IDs alone do not prove answer correctness.

## Run

Run from the repository root with Python 3.11, the backend dependencies installed, and host Ollama
running with `embeddinggemma` and `qwen2.5:3b` available:

```bash
backend/.venv/bin/python evaluation/run.py
backend/.venv/bin/python evaluation/run.py --top-k 5
```

On Windows use `backend\.venv\Scripts\python.exe` instead. Override `OLLAMA_BASE_URL` if the model
server is not at `http://127.0.0.1:11434`. No running frontend, API or database is required.

Options: `--dataset`, `--chunk-size` (default 250 characters), `--overlap` (50 characters),
`--top-k` (3, allowed 1–10), and `--output`. Existing output files are refused. Each case saves
partial progress to a timestamped JSON report under `reports/`; model failures are recorded per case
and produce a nonzero exit status. Generation timing includes validation and any retry.

## Read the report

- `gold_quote_coverage`: fraction of expected quotes fully covered by the union of retrieved chunk
  spans; a quote may cross chunks. It is null for unanswerable questions.
- `found_matches_expected`: whether the model's found/abstention decision matches the fixture.
- `schema_and_ids_valid`: structured answer validation succeeded, including allowed citation IDs.
- `timing_seconds`: query embedding, retrieval, generation/validation and total per-question latency.
- `manual_review`: fill answer correctness, required-fact completeness, citation support and language
  checks manually. Null means unreviewed, not passed.

Summary means use available retrieval scores only; check `retrieval_scored_cases` and `errors` alongside
coverage. A successful process exit is not proof of correct answers.

This runner reuses the application's chunking, embeddings and structured generation functions, but
uses **in-memory cosine retrieval**. It does not exercise HTTP routes, pgvector, OCR, or permissions,
and never changes the application's document database. The older `samples/evaluation.json` and
`backend/experiments/evaluate_rag.py` remain a separate dataset/runner with a different schema.

The four-question fixture is a starter set, not a representative accuracy benchmark. Compare runs
using the same model digests and inputs, change one parameter at a time, and distinguish cold-model
loading from warm inference. Expand the dataset after reviewing the baseline.
