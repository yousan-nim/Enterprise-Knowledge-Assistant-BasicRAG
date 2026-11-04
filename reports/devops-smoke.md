# DevOps verification — 2026-11-04

Branch: `feat/devops-one-command`.

- `./scripts/dev.sh` built the API image, started PostgreSQL and Ollama, downloaded both models,
  and returned successfully with backend, database and Ollama healthy.
- An empty, separate test PostgreSQL volume initialized the vector extension and both tables.
  That test project's container and volume were removed afterwards.
- All 84 automated tests passed on the host and inside the backend image, including isolated
  PostgreSQL integration tests. Automated model calls use mocks.
- A separate manual API smoke test used real containerized Ollama and pgvector:
  upload returned `201`; question returned `200` with `found: true`, citation `chunk-1`,
  source page `1` and the correct THB 500 limit; deletion returned `204`.
  The test refused to replace existing documents and removed its own uploaded document afterwards.
- Rerunning `./scripts/dev.sh` also completed successfully using cached images and model volumes.
- The real answer was: “The daily travel reimbursement limit is THB 500.”
- Cold chat loading and generation took about 80 seconds on CPU with approximately 4 GB allocated
  to Docker. This is one local observation, not a general performance benchmark.

GitHub Actions is configured to run tests and build the image. Its remote result is separate
from these local checks; model downloads/inference are not part of CI.
