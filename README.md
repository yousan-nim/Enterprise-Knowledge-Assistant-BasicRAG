# Enterprise Knowledge Assistant — Basic RAG

A local document question-answering API built with **FastAPI, Ollama and PostgreSQL + pgvector**.
Upload a TXT, Markdown or text-based PDF, ask questions, and inspect cited passages with page numbers.

## Run with one command

Prerequisites: Docker Desktop running (or Docker Engine with Compose v2), internet for the first download,
and a POSIX shell (macOS/Linux or Windows WSL). Recommended: a machine with 16 GB RAM, at least
8 GB assigned to Docker and 15 GB free disk for images and models.

From the cloned repository:

```bash
./scripts/dev.sh
```

Open **http://127.0.0.1:8080/docs**. No Python installation, API key or separate Ollama installation is required.
The script generates a private, Git-ignored `.env` if none exists, builds the backend, starts PostgreSQL
and Ollama, downloads `embeddinggemma` and `qwen2.5:3b`, and waits for the API to become healthy.
The first run downloads several GB and may take several minutes; subsequent runs reuse Docker volumes.

This portable setup runs Ollama on CPU. On a Mac it does not use native Metal acceleration, so generation
can be slower than running Ollama directly on the host. This repository currently exposes a Swagger API;
the Next.js frontend is not implemented. There is no OCR or authentication. Services published to the host
bind to loopback for local demos.

### Try the workflow

1. In Swagger, call `POST /api/v1/documents` using `samples/company-handbook.md` or a text-based PDF.
2. Call `POST /api/v1/questions` with:

   ```json
   {"question": "How much can I claim for travel expenses?", "top_k": 2}
   ```

3. Inspect `answer`, `citation_ids` and `sources` (including `page`, `text` and similarity `score`).
4. Call `GET /api/v1/documents` to find the document ID, then `DELETE /api/v1/documents/{document_id}` to remove it.

One document is indexed at a time. A successful upload replaces the previous document; a failed ingestion
preserves it. Similarity is not confidence, and valid citations do not prove factual correctness. Review
original passages. Scanned pages are not read; PDFs containing no readable text are rejected.

## Operate the stack

```bash
docker compose ps                       # Service status
docker compose logs -f backend models    # API and model download logs
docker compose down                     # Stop; retain documents and models
./scripts/dev.sh                        # Start again
```

To change ports, edit `API_PORT` (default `8080`) or `POSTGRES_PORT` (default `5433`) in `.env`, then rerun
the startup command. PostgreSQL credentials persist in its volume; editing `.env` alone does not change
an existing database password. `docker compose down -v` deletes documents and downloaded models.
If startup fails, inspect the logs above and rerun after resolving the error. A model-download failure
prevents the backend from starting rather than reporting success with missing models.

## Architecture

```text
Upload → Parse pages → Chunk each page → Ollama embeddings → PostgreSQL vector(768)
Question → Ollama embedding → pgvector exact cosine search → LLM → Answer + citations
```

- `backend/app/routes/`: versioned HTTP endpoints under `/api/v1`
- `backend/app/services/`: parsing, chunking, model calls, ingestion and grounded generation
- `backend/app/storage/postgres.py`: transactional document replacement and vector search
- `infra/postgres/`: extension bootstrap, initial schema and SQL checks
- `backend/tests/`: unit, API and isolated PostgreSQL integration tests
- `samples/`, `learning/`, `reports/`: sample documents, exercises and evaluation evidence
- `.github/workflows/ci.yml`: automated tests and backend image build

SQLite storage and Python cosine search remain as learning baselines and test helpers; the live API uses
PostgreSQL. SQLite documents are not automatically migrated. PostgreSQL initialization scripts run only
on an empty volume; see [database setup](infra/postgres/README.md) for an existing volume.

## Develop and test without containers for the API

Requires Python 3.11 and host Ollama with `embeddinggemma` and `qwen2.5:3b` downloaded.

```bash
python3.11 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
docker compose up -d --wait postgres
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Run `./scripts/dev.sh` once first to generate `.env`, or copy `.env.example` to `.env` and replace the
password. Host Python defaults to Ollama at `http://127.0.0.1:11434`; set `OLLAMA_BASE_URL` to override.
The container uses `http://ollama:11434`. Backend PostgreSQL settings use `.env` with process environment overrides.

```bash
RUN_POSTGRES_TESTS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py' -q
```

Omit `RUN_POSTGRES_TESTS=1` for tests without a running PostgreSQL server. Integration tests create and
clean up randomly named schemas; they do not replace the application's real documents. Model responses
are mocked in the automated suite. CI runs database integration tests and builds the image without downloading LLMs.

Local verification evidence: [DevOps smoke report](reports/devops-smoke.md).

Learning notes: [scope](docs/SPEC.md), [learning path](docs/LEARNING_PATH.md).

Container setup follows [Ollama Docker documentation](https://docs.ollama.com/docker),
[Compose dependency conditions](https://docs.docker.com/compose/how-tos/startup-order/), and
[pgvector documentation](https://github.com/pgvector/pgvector).
