"use client";
import { useEffect, useRef, useState } from "react";
import { Icon } from "./icon";

const acknowledgmentKey = "folio:guide-acknowledged:v1";
const titles = [
  "ยินดีต้อนรับสู่ Folio",
  "เริ่มใช้งานใน 4 ขั้นตอน",
  "ก่อนเริ่มทดลองใช้งาน",
];

export function GuideButton() {
  return (
    <button
      className="icon-button about-button"
      aria-label="About this workspace"
      onClick={() =>
        (
          document.getElementById("project-guide") as HTMLDialogElement | null
        )?.showModal()
      }
    >
      <Icon name="info" />
    </button>
  );
}

export function ProjectGuide() {
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [step, setStep] = useState(0);
  const [acknowledged, setAcknowledged] = useState(false);
  useEffect(() => {
    let accepted = false;
    try {
      accepted = localStorage.getItem(acknowledgmentKey) === "true";
    } catch {
      /* Storage may be disabled; the guide remains available. */
    }
    if (!accepted && !dialog.current?.open) dialog.current?.showModal();
  }, []);
  useEffect(() => {
    if (dialog.current?.open) heading.current?.focus();
  }, [step]);
  function finish() {
    if (!acknowledged) return;
    try {
      localStorage.setItem(acknowledgmentKey, "true");
    } catch {
      /* Acknowledgment still works for this visit. */
    }
    dialog.current?.close();
  }
  return (
    <dialog
      id="project-guide"
      ref={dialog}
      className="about-dialog glass project-guide"
      aria-labelledby="guide-title"
      lang="th"
      onClose={() => {
        setStep(0);
        setAcknowledged(false);
      }}
    >
      <button
        className="icon-button dialog-close"
        aria-label="Close introduction"
        onClick={() => dialog.current?.close()}
      >
        <Icon name="close" />
      </button>
      <p className="eyebrow">FOLIO · PORTFOLIO DEMO</p>
      <p className="guide-progress" aria-live="polite">
        หน้า {step + 1} จาก 3 ·{" "}
        {step === 0
          ? "เกี่ยวกับโปรเจกต์"
          : step === 1
            ? "วิธีใช้งาน"
            : "รับทราบก่อนใช้งาน"}
      </p>
      <h2 id="guide-title" ref={heading} tabIndex={-1}>
        {titles[step]}
      </h2>
      {step === 0 && (
        <div className="guide-content">
          <p>
            โปรเจกต์ Portfolio ของ{" "}
            <strong>Pongchanok Nuamteam (yousan-nim)</strong>{" "}
            สำหรับสาธิตการทำงานเบื้องต้นของ <strong>Basic RAG + OCR</strong>{" "}
            ตั้งแต่อ่านเอกสาร ค้นข้อมูล ไปจนถึงสร้างคำตอบพร้อมข้อความอ้างอิง
          </p>
          <a
            className="guide-repository"
            href="https://github.com/yousan-nim/Enterprise-Knowledge-Assistant-BasicRAG"
            target="_blank"
            rel="noopener noreferrer"
          >
            ดู source code บน GitHub ↗
            <small>yousan-nim / Enterprise-Knowledge-Assistant-BasicRAG</small>
          </a>
          <p>
            พัฒนาด้วย Next.js, FastAPI, PostgreSQL/pgvector และ Ollama โดย OCR
            รองรับภาษาไทยและอังกฤษ เป็นระบบสาธิตเพื่อการเรียนรู้
            ไม่ใช่บริการที่พร้อมใช้งานจริงในองค์กร
          </p>
        </div>
      )}
      {step === 1 && (
        <ol className="guide-steps">
          <li>
            <strong>เลือกเอกสาร</strong>
            <p>
              กด Try the sample document หรืออัปโหลด PDF, TXT หรือ Markdown
              ขนาดไม่เกิน 1 MiB รองรับ PDF สูงสุด 50 หน้า และหน้าที่ต้องใช้ OCR
              ไม่เกิน 5 หน้า
            </p>
          </li>
          <li>
            <strong>รอเตรียมข้อมูล</strong>
            <p>
              ระบบอ่านข้อความหรือทำ OCR แบ่งเป็น chunks และสร้าง embeddings
              เก็บใน pgvector รอจนเอกสารพร้อมก่อนถาม
            </p>
          </li>
          <li>
            <strong>ถามใน Document Q&amp;A</strong>
            <p>
              พิมพ์คำถามเกี่ยวกับเอกสาร แล้วกดส่ง
              ระบบจะค้นข้อความที่เกี่ยวข้องและให้โมเดลสร้างคำตอบ
            </p>
          </li>
          <li>
            <strong>ตรวจข้อความอ้างอิง</strong>
            <p>
              เปิด cited passages เพื่อตรวจเนื้อหาต้นฉบับ เลขหน้า และที่มาจาก
              OCR หรือเลือก API Flows ใน navbar เพื่อดูขั้นตอนของระบบ
            </p>
          </li>
        </ol>
      )}
      {step === 2 && (
        <div className="guide-content">
          <ul className="guide-notes">
            <li>
              คำตอบจาก AI และ OCR อาจผิดพลาด ควรตรวจเอกสารต้นฉบับเสมอ ค่า
              similarity ไม่ใช่ความมั่นใจว่าคำตอบถูกต้อง
            </li>
            <li>
              ระบบเก็บเอกสารครั้งละหนึ่งฉบับ การอัปโหลดใหม่แทนที่ฉบับเดิม
              เอกสารคงอยู่ในฐานข้อมูลจนกว่าจะถูกแทนที่หรือลบ
            </li>
            <li>
              เดโมนี้ไม่มีระบบล็อกอินหรือแยกข้อมูลรายผู้ใช้ หากแชร์ instance
              จะใช้เอกสารเดียวกัน
              กรุณาใช้ข้อมูลตัวอย่างและไม่อัปโหลดข้อมูลลับหรือข้อมูลส่วนบุคคล
            </li>
            <li>
              Free chat ไม่ค้นเอกสาร แต่ละคำถามตอบอิสระ
              ไม่ส่งข้อความก่อนหน้าเป็นบริบท
              ประวัติแชตแสดงเฉพาะระหว่างใช้งานหน้านี้และหายเมื่อโหลดใหม่หรือเปลี่ยนหน้า
            </li>
          </ul>
          <label className="guide-ack">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
            />
            <span>
              ฉันอ่านและรับทราบวัตถุประสงค์ วิธีใช้งาน และข้อจำกัดของเดโมนี้แล้ว
            </span>
          </label>
          <p className="guide-storage">
            การรับทราบบันทึกเฉพาะในเบราว์เซอร์นี้ เปิดอ่านซ้ำได้จากปุ่ม About
            (i)
          </p>
        </div>
      )}
      <div className="guide-actions">
        {step > 0 && (
          <button className="button" onClick={() => setStep(step - 1)}>
            ย้อนกลับ
          </button>
        )}
        {step < 2 ? (
          <button className="button primary" onClick={() => setStep(step + 1)}>
            ถัดไป <Icon name="chevron" size={16} />
          </button>
        ) : (
          <button
            className="button primary"
            disabled={!acknowledged}
            onClick={finish}
          >
            รับทราบและเริ่มใช้งาน
          </button>
        )}
      </div>
    </dialog>
  );
}
