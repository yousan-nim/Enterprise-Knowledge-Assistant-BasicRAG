# Enterprise Knowledge Assistant — Basic RAG

Learning scaffold → portfolio project. โค้ดการทำงานจะเขียนเองทีละบท

**สถานะ:** FastAPI รองรับ upload TXT/Markdown/PDF, ถามตอบพร้อม citations และจัดการเอกสาร โดยใช้ PostgreSQL + pgvector และ Ollama

## Product
ผู้ใช้ใส่เอกสารนโยบายบริษัทสมมติ แล้วถามคำถามภาษาไทยหรืออังกฤษ ระบบค้นข้อความที่เกี่ยวข้องและตอบพร้อมชื่อเอกสารและแหล่งอ้างอิง เมื่อไม่มีข้อมูลต้องแจ้งว่าไม่พบ

## Intended stack
- Frontend: Next.js + TypeScript (ตั้งค่าเมื่อถึงบท UI)
- Backend: Python + FastAPI
- Models: Ollama — embedding model แยกจาก chat model
- Storage: PostgreSQL + pgvector (768 dimensions); SQLite retained as a learning baseline

## Layout
```text
backend/
  app/
    main.py                 # สร้าง FastAPI และเชื่อม routes
    config/config.py        # อ่าน environment settings
    schemas/schemas.py      # structured model answers
    schemas/http.py         # API request/response models
    api_docs/api_docs.py    # Swagger descriptions and examples
    routes/
      router.py             # รวม endpoints ใต้ /api/v1
      health.py             # API liveness
      chat.py               # ถามโมเดลโดยไม่ค้นเอกสาร
      documents.py          # รับเอกสารและเรียก ingestion
      questions.py          # รับคำถามและเรียก RAG
    services/
      chunking.py           # ข้อความ → chunks
      ollama.py             # เรียก embed / chat
      ingestion.py          # อ่านเอกสาร → chunk → embed → store
      retrieval.py          # embed question → cosine → top-k
      generation.py         # สร้าง prompt → answer
    storage/
      memory.py             # เก็บข้อมูลในหน่วยความจำ
  tests/                    # unit and optional PostgreSQL integration tests
  data/                     # ข้อมูล local ไม่เข้า Git
frontend/                   # จองที่ไว้ ตั้งค่า Next.js ในบท UI
samples/                    # เอกสารสมมติและคำถามทดสอบ
learning/                   # บันทึกการทดลองของผู้เรียน
reports/                    # ผลวัดสำหรับ portfolio
```

อ่าน [ขอบเขต](docs/SPEC.md) → [ลำดับฝึก](docs/LEARNING_PATH.md) → เริ่ม `backend/app/main.py`

## Learning rule
ทีละบท: อธิบาย input/output → เขียนเอง → ทดสอบ → บันทึกผล → อธิบายกลับ
อย่าระบุว่าฟีเจอร์เสร็จหรือ production-ready จนกว่าจะมีหลักฐานจริง

## Commands
Run from the repository root with the existing backend virtual environment and Ollama models:

```bash
docker compose up -d --wait postgres
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

PostgreSQL settings are read from the root `.env`, with process environment overrides.
SQLite documents are not migrated automatically; upload again after switching.
Run tests including real PostgreSQL checks:

```bash
RUN_POSTGRES_TESTS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py' -q
```

## Portfolio evidence
เก็บ architecture, retrieval examples, failure cases, evaluation report และ demo จากระบบที่ทำจริง ไม่ใส่ผล benchmark ที่ยังไม่ได้วัด

## API routes

- `GET /api/v1/health`
- `POST /api/v1/chat`
- `POST /api/v1/documents` (multipart file upload)
- `GET /api/v1/documents`
- `DELETE /api/v1/documents/{document_id}`
- `POST /api/v1/questions`

Swagger stays at `/docs`; OpenAPI stays at `/openapi.json`.
Unversioned endpoint paths have been replaced. Update external clients to `/api/v1`.

## PostgreSQL + pgvector (first migration step)

Local database setup and verification: [infra/postgres/README.md](infra/postgres/README.md).
The backend now uses PostgreSQL for upload, list, delete and exact cosine retrieval.
