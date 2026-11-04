# Local PostgreSQL + pgvector

Run commands from the repository root. Docker Desktop must be running.

For a new checkout, copy `.env.example` to `.env` and replace the password.
The initial setup on this machine already generated an ignored `.env` with a random password.

```bash
docker compose config --quiet
docker compose up -d --wait postgres
docker compose ps
docker compose exec postgres psql -U rag -d knowledge -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
docker compose exec postgres psql -U rag -d knowledge -c "SELECT '[1,0]'::vector <=> '[0,1]'::vector AS cosine_distance;"
```

Defaults: host `127.0.0.1`, port `5433`, database `knowledge`, user `rag`.
Password is in the local `.env`. Both Compose and the backend read these settings;
the backend now uses PostgreSQL. Existing SQLite documents are not migrated; upload again.

`init.sql` runs only when the database volume is first initialized. For an existing
volume missing the extension, run `CREATE EXTENSION IF NOT EXISTS vector;` using psql.
Changing credentials in `.env` does not change an already initialized database's credentials.

Stop while keeping the database:

```bash
docker compose down
```

The named volume retains data across container restarts and recreation.
`docker compose down -v` deletes the database volume and its data; avoid it for normal shutdown.
This is a local development database, not a production deployment.

References: https://github.com/pgvector/pgvector and https://docs.docker.com/compose/how-tos/startup-order/

## Schema (second migration step)

`schema.sql` creates `documents` (UUID ID, source, embedding model) and `chunks`
(text, page, extraction method, position and `vector(768)`). UUID IDs match ingestion's
`uuid4()` IDs. Chunk IDs are unique within each document. Deleting a document cascades
to its chunks. Zero vectors are rejected because cosine similarity requires nonzero vectors.
The current embedding model is `embeddinggemma`; a different dimension requires an
explicit schema change and re-embedding. Search initially uses exact distance, without HNSW.

On an existing initialized volume, apply the additive initial schema explicitly:

```bash
docker compose exec -T postgres psql -U rag -d knowledge -v ON_ERROR_STOP=1 < infra/postgres/schema.sql
docker compose exec -T postgres psql -U rag -d knowledge -v ON_ERROR_STOP=1 < infra/postgres/test_schema.sql
```

On a fresh volume Docker runs `init.sql` then `schema.sql` automatically. Reapplying
this initial script does not modify existing tables; future schema changes need migrations.
The integration check uses a transaction and rolls its fixtures back. Backend routes now use PostgreSQL for ingestion and retrieval.

## Python storage replacement tests

`backend/app/storage/postgres.py` now provides `replace_chunks()` alongside
`connect()` and `get_documents()`. Replacement is atomic and validates vectors
before opening a connection. The API now uses PostgreSQL for upload, list, delete and retrieval.

Run the full suite including real PostgreSQL storage tests from the repository root:

```bash
RUN_POSTGRES_TESTS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py' -q
```

Integration tests create an isolated randomly named schema, then drop only that
schema on cleanup. They do not replace documents in the application's public schema.
Without `RUN_POSTGRES_TESTS=1`, the database integration tests are skipped.
