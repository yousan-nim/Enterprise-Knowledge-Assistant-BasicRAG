import type { Metadata } from "next";
import Link from "next/link";
import { SiteNav } from "@/components/site-nav";

export const metadata: Metadata = {
  title: "API Flows — Folio",
  description:
    "Explore the six RAG backend endpoints, document ingestion, OCR, pgvector retrieval and native Ollama inference.",
};

export default function ApiFlowsPage() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="Folio home">
          folio<span className="brand-period">.</span>
        </Link>
        <SiteNav />
      </header>
      <main className="flow-page" id="conversation" tabIndex={-1}>
        <div className="flow-heading">
          <div>
            <p className="eyebrow">BEHIND THE ANSWER</p>
            <h1>Explore the API flows.</h1>
            <p>
              ติดตามทั้ง 6 endpoints ตั้งแต่อัปโหลดและ OCR ไปจนถึงค้นด้วย
              pgvector และสร้างคำตอบด้วย Ollama
            </p>
          </div>
          <a
            className="flow-open"
            href="/diagrams/api-endpoints.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open full page ↗
          </a>
        </div>
        <p className="flow-hint">
          เลือก endpoint ภายในแผนภาพเพื่อข้ามไปดูขั้นตอน ·
          บนมือถือเลื่อนภาพในแนวนอนได้
        </p>
        <iframe
          className="flow-frame"
          src="/diagrams/api-endpoints.html"
          title="Six API endpoint process diagrams"
          sandbox="allow-same-origin"
        />
      </main>
    </div>
  );
}
