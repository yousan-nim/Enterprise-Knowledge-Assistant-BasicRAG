# Learning path

ทุกบทให้เก็บคำถาม สมมติฐาน ผลทดลอง และคำอธิบายด้วยคำตนเองใน `learning/`.

| บท | งานที่เขียนเอง | ตรวจว่าผ่านอย่างไร |
|---|---|---|
| 01 | FastAPI app + GET /api/v1/health | รันบน loopback และเปิด /docs ได้ |
| 02 | Ollama chat client | ให้โมเดลอ่าน sample ทั้งฉบับแล้วตอบได้; ยังไม่เรียกว่า RAG |
| 03 | chunk_text | ทดสอบข้อความว่าง ขอบเขต chunk และ overlap ที่ไม่ถูกต้อง |
| 04 | embedding client | อธิบายจำนวน vectors และมิติได้; reject malformed response |
| 05 | in-memory store + cosine + top-k | ตรวจอันดับด้วย vectors เล็กที่คำนวณมือได้ |
| 06 | document ingestion | รับ MD/TXT แล้วตรวจ chunks และ metadata ที่เก็บได้ |
| 07 | question endpoint + generation | เห็น retrieved excerpts ก่อนเห็นคำตอบ; ส่งคืนแหล่งอ้างอิง |
| 08 | missing-answer / Thai / citations | แยกค้นผิดออกจากตอบผิด ไม่ถือว่ามี citation แล้วคำตอบถูก |
| 09 | Next.js upload/chat UI | แสดง loading, error, empty state และ source excerpts |
| 10 | evaluation + README + demo | รายงานผลจริงพร้อม model/config และวิธีทำซ้ำ |

## Start here — บท 01
ไฟล์: `backend/app/main.py`, `backend/app/routes/health.py`.
โจทย์: FastAPI คืออะไร? route รับอะไรและตอบอะไร? ทดลอง HTTP GET และแยก liveness ออกจาก Ollama readiness.
เขียนเองก่อน แล้วขอ review โค้ดได้ ยังไม่ต้องสร้าง RAG ทั้งระบบในบทนี้
