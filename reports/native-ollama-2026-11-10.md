# Native Ollama performance change — 2026-11-10

- Docker backend now uses host Ollama through the opt-in native Compose override.
- Local `.env` selects the native override for subsequent Compose commands (not committed).
- Native and Docker model digests match: embeddinggemma `85462619ee72`, qwen2.5:3b `357c53fb659c`.
- Same embedding input: both vectors have 768 dimensions; cosine similarity 0.9999933477.
- `ollama ps` reports both models fully on GPU. Docker Ollama stopped; its volume retained.
- Actual browser → Next proxy → FastAPI → pgvector → host Ollama sample smoke passed:
  upload ~0.89 s; grounded question ~18.65 s; correct THB 500 answer with chunk-2 citation.
  Smoke removed only its own temporary sample document.
- Earlier CPU test of 32 generation tokens exceeded 100 s; native warm test took 4.18 s.
  These short-generation timings are not an end-to-end RAG latency guarantee.
- Cold native model loads were still slow (embedding comparison ~32 s while both runtimes were active).
  GPU inference reduces compute latency but does not remove cold starts, memory pressure or generation time.
- 106 backend tests passed including PostgreSQL/OCR and shell launcher mode/argument tests.
- Base Compose config still selects Docker Ollama; native model check has no Docker Ollama dependency.
- PowerShell native-mode assertions added to the existing Windows CI launcher tests.
- No API contracts, stored document content or embedding index were changed by this configuration update.
- Streaming is not implemented in this change; structured RAG answers are still validated before display.
