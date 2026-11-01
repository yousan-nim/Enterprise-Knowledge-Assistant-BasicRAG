# Enterprise Knowledge Assistant — Basic RAG

Learning scaffold → portfolio project. โค้ดการทำงานจะเขียนเองทีละบท

**สถานะ:** มีเฉพาะโครงสร้างและโจทย์ ยังไม่มี application, dependencies หรือ server ที่รันได้

## Product
ผู้ใช้ใส่เอกสารนโยบายบริษัทสมมติ แล้วถามคำถามภาษาไทยหรืออังกฤษ ระบบค้นข้อความที่เกี่ยวข้องและตอบพร้อมชื่อเอกสารและแหล่งอ้างอิง เมื่อไม่มีข้อมูลต้องแจ้งว่าไม่พบ

## Intended stack
- Frontend: Next.js + TypeScript (ตั้งค่าเมื่อถึงบท UI)
- Backend: Python + FastAPI
- Models: Ollama — embedding model แยกจาก chat model
- Basic storage: in-memory ก่อน แล้วเพิ่ม SQLite persistence
- Later: PostgreSQL + pgvector หลังมี baseline ที่วัดได้

## Layout
```text
backend/
  app/
    main.py                 # สร้าง FastAPI และเชื่อม routes
    config.py               # อ่าน environment settings
    schemas.py              # request/response models
    api/
      health.py             # readiness ของ API / Ollama
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
  tests/                    # โจทย์ทดสอบ ยังไม่มี tests
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
ยังไม่มีคำสั่ง run/build ที่ใช้งานได้ เพราะไฟล์เป็นโจทย์เปล่า เมื่อทำบท 01 ให้สร้าง virtual environment ติดตั้ง FastAPI/Uvicorn และบันทึกเวอร์ชันที่ใช้จริงก่อนเพิ่มคำสั่ง run ที่นี่

## Portfolio evidence
เก็บ architecture, retrieval examples, failure cases, evaluation report และ demo จากระบบที่ทำจริง ไม่ใส่ผล benchmark ที่ยังไม่ได้วัด
