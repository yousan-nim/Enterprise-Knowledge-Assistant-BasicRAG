# RAG evaluation

Run from the repository root with Ollama running:

```sh
PYTHONPATH=backend backend/.venv/bin/python backend/experiments/evaluate_rag.py
```

Default top-k=1 makes this two-chunk document a selective retrieval exercise. Compare with `--top-k 2`, which sends all chunks and is not a meaningful retrieval challenge.

Each timestamped JSON includes dataset version, code/data hashes, installed model digests, config, retrieved evidence, model output, errors and wall-clock latency (query embedding + search + generation + validation retries). Document indexing time is excluded.

Automated checks: schema/allowed IDs, expected found status, exact evidence-quote coverage. A quote split across chunks may fail coverage even if the combined context contains enough evidence. This is not semantic Recall@k or a factual-accuracy score.

Fill `manual_review` for answer correctness, complete conditions, citation support and requested language. The canonical Thai abstention is currently used even for English questions; record that limitation honestly. Null means unreviewed, not passed.

The dataset is a small development set, not a holdout benchmark. Do not claim production accuracy from these ten cases. Reports contain only fictional sample data; never commit confidential documents or answers.
