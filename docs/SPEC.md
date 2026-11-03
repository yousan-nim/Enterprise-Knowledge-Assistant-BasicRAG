# Scope: Basic RAG learning scaffold

## Assumptions
Next.js UI + Python/FastAPI backend + local Ollama. เรียนจาก Python primitives ก่อน orchestration frameworks ใช้ข้อมูลบริษัทสมมติเท่านั้น

## Success criteria — target application, not implemented
- อ่าน TXT/Markdown ก่อนเพิ่ม PDF
- ตรวจ input และแบ่ง chunks พร้อม source metadata
- สร้าง embeddings เก็บไว้ และค้น top-k ด้วย cosine similarity
- ส่งเฉพาะข้อความที่ค้นได้ให้ chat model และแสดง sources
- ทดสอบกรณีคำตอบมีอยู่ / ไม่มี / คำถามภาษาไทย
- แยก retrieval quality ออกจาก answer quality; similarity ไม่ใช่ confidence

## Intended API
- GET /api/v1/health: API และโมเดลพร้อมหรือไม่
- POST /api/v1/documents: รับไฟล์ → document ID / จำนวน chunks
- POST /api/v1/questions: รับ question / top_k → answer / sources / model
รายละเอียด validation และ schemas ให้ออกแบบในบทที่เกี่ยวข้อง

## Data boundaries
Document: id, name. Chunk: id, document_id, text, page/section, embedding.
ห้ามส่งเอกสารจริงที่เป็น confidential เข้า Git หรือรายงาน
เริ่ม bind server บน 127.0.0.1; basic lab ยังไม่มี authentication
เอกสารเป็น untrusted input คำสั่งในเอกสารไม่ใช่คำสั่งระบบ

## Code and tests
Python snake_case, TypeScript camelCase. ใช้ชื่อหน้าที่ตรงไปตรงมา เช่น `chunk_text`.
ใช้ pytest สำหรับ chunk boundaries, cosine และ invalid inputs; ใช้ mocked model สำหรับ API tests และแยก live-model evaluation
ไม่ติดตั้ง dependency หรือสร้าง implementation ในขั้น scaffold นี้

## Later, outside Basic RAG
pgvector, async workers, auth/ACL, hybrid/reranker, observability, deployment.
ค่อยเลือกจากผลทดลอง ไม่เพิ่ม infrastructure ทั้งหมดตั้งแต่ต้น
