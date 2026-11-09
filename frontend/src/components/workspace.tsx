"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Answer, api, DocumentInfo, Source, validateFile } from "@/lib/api";
import { Documents } from "./documents";
import { Evidence } from "./evidence";
import { Icon } from "./icon";
type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources: Source[];
  citations: string[];
  found?: boolean;
};
const suggestions = [
  "What are the key takeaways?",
  "What should I pay attention to?",
  "ค่าเดินทางเบิกได้สูงสุดเท่าไร?",
];
function Logo({ small = false }: { small?: boolean }) {
  return (
    <span
      className={`logo-mark ${small ? "small-mark" : ""}`}
      aria-hidden="true"
    >
      <span />
      <span />
      <span />
      <span />
    </span>
  );
}
export function Workspace() {
  const [document, setDocument] = useState<DocumentInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [sampling, setSampling] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [asking, setAsking] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [mode, setMode] = useState<"documents" | "chat">("documents");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeEvidence, setActiveEvidence] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const question = useRef<HTMLTextAreaElement>(null);
  const info = useRef<HTMLDialogElement>(null);
  const documentId = useRef<string | null>(null);
  const busy = uploading || asking || deleting || sampling;
  const evidence = messages.find((message) => message.id === activeEvidence);
  function clearConversation() {
    setMessages([]);
    setActiveEvidence(null);
    setInput("");
  }
  async function refresh() {
    setLoading(true);
    try {
      const docs = await api<DocumentInfo[]>("/documents");
      const next = docs[0] || null;
      if (documentId.current !== (next?.document_id || null)) {
        clearConversation();
        documentId.current = next?.document_id || null;
      }
      setDocument(next);
      setConnected(true);
      setError(null);
    } catch (e) {
      setConnected(false);
      setError(e instanceof Error ? e.message : "Could not load your library.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
  }, []); // Load persisted document metadata once, not a pretend document.
  useEffect(() => {
    if (messages.length || asking)
      bottom.current?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
        block: "nearest",
      });
  }, [messages, asking]);
  async function upload(file: File) {
    setPendingFile(null);
    setError(null);
    setNotice(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api<{
        document_id: string;
        source: string;
        chunks: number;
      }>("/documents", { method: "POST", body: form });
      documentId.current = result.document_id;
      setDocument({ ...result, embedding_model: "embeddinggemma" });
      setConnected(true);
      clearConversation();
      setNotice(`${result.source} is ready. Ask your first question.`);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not upload the document. Your existing document is unchanged.",
      );
    } finally {
      setUploading(false);
    }
  }
  function chooseFile(file: File) {
    if (busy || loading) return;
    const invalid = validateFile(file);
    if (invalid) {
      setError(invalid);
      return;
    }
    if (document) {
      setPendingFile(file);
      setError(null);
    } else void upload(file);
  }
  async function sample() {
    if (busy || loading) return;
    setSampling(true);
    setError(null);
    try {
      const response = await fetch("/sample-handbook.md");
      if (!response.ok) throw new Error("The sample document is unavailable.");
      chooseFile(
        new File([await response.blob()], "company-handbook.md", {
          type: "text/markdown",
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open the sample.");
    } finally {
      setSampling(false);
    }
  }
  async function remove() {
    if (!document || busy) return;
    setDeleting(true);
    setError(null);
    try {
      await api(`/documents/${encodeURIComponent(document.document_id)}`, {
        method: "DELETE",
      });
      documentId.current = null;
      setDocument(null);
      clearConversation();
      setNotice("Document removed. A fresh page awaits.");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not remove the document.",
      );
    } finally {
      setDeleting(false);
    }
  }
  async function ask(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy || loading || (mode === "documents" && !document)) return;
    const userId = crypto.randomUUID();
    setMessages((previous) => [
      ...previous,
      { id: userId, role: "user", text, sources: [], citations: [] },
    ]);
    setInput("");
    setAsking(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api<Answer | { answer: string }>(
        mode === "documents" ? "/questions" : "/chat",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            mode === "documents"
              ? { question: text, top_k: 3 }
              : { question: text },
          ),
        },
      );
      const id = crypto.randomUUID();
      const grounded = "sources" in result;
      setMessages((previous) => [
        ...previous,
        {
          id,
          role: "assistant",
          text: result.answer,
          sources: grounded ? result.sources : [],
          citations: grounded ? result.citation_ids : [],
          found: grounded ? result.found : undefined,
        },
      ]);
      setActiveEvidence(grounded ? id : null);
    } catch (e) {
      setMessages((previous) =>
        previous.filter((message) => message.id !== userId),
      );
      setInput(text);
      setError(
        e instanceof Error
          ? e.message
          : "Could not get an answer. Please try again.",
      );
    } finally {
      setAsking(false);
      setTimeout(() => question.current?.focus(), 0);
    }
  }
  function changeMode(next: "documents" | "chat") {
    if (next === mode || busy) return;
    setMode(next);
    clearConversation();
    setError(null);
    setNotice(null);
  }
  function showEvidence(id: string) {
    setActiveEvidence(id);
    setTimeout(() => {
      const panel = window.document.getElementById("evidence");
      panel?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
        block: "nearest",
      });
      panel?.focus({ preventScroll: true });
    }, 0);
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Folio home">
          <Logo />
          <span>
            folio<span className="brand-period">.</span>
          </span>
          <span className="brand-divider" />
          <small>KNOWLEDGE WORKSPACE</small>
        </a>
        <div className="top-actions">
          <span
            className={`connection ${connected === false ? "offline" : ""}`}
            role="status"
          >
            <span />
            {connected === null
              ? "Connecting…"
              : connected
                ? "API connected"
                : "API unavailable"}
          </span>
          <button
            className="icon-button about-button"
            aria-label="About this workspace"
            onClick={() => info.current?.showModal()}
          >
            <Icon name="info" />
          </button>
        </div>
      </header>
      <main className="main-shell">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">LESS SEARCHING. MORE UNDERSTANDING.</p>
            <h1>
              A little clarity.<span> From your documents.</span>
            </h1>
            <p>Bring your knowledge. Leave with a clearer answer.</p>
          </div>
          <span className="workspace-label">
            <span className="tiny-dot" />
            YOUR LOCAL SPACE
          </span>
        </div>
        <div className="workspace-grid">
          <Documents
            document={document}
            loading={loading}
            busy={busy}
            uploading={uploading}
            deleting={deleting}
            connected={connected}
            onFile={chooseFile}
            onSample={() => void sample()}
            onDelete={() => void remove()}
            onRefresh={() => void refresh()}
            pendingFile={pendingFile}
            onConfirmUpload={() => {
              if (pendingFile) void upload(pendingFile);
            }}
            onCancelUpload={() => setPendingFile(null)}
          />
          <section
            className="conversation glass"
            id="conversation"
            aria-label="Conversation"
            tabIndex={-1}
          >
            <header className="conversation-header">
              <div
                className="mode-switch"
                role="group"
                aria-label="Conversation mode"
              >
                <button
                  aria-pressed={mode === "documents"}
                  onClick={() => changeMode("documents")}
                  disabled={busy}
                >
                  <Icon name="book" size={16} />
                  Document Q&amp;A
                </button>
                <button
                  aria-pressed={mode === "chat"}
                  onClick={() => changeMode("chat")}
                  disabled={busy}
                >
                  <Icon name="spark" size={16} />
                  Free chat
                </button>
              </div>
              <button
                className="icon-button"
                aria-label="Clear conversation"
                title="Clear conversation"
                onClick={clearConversation}
                disabled={busy || !messages.length}
              >
                <Icon name="refresh" size={17} />
              </button>
            </header>
            <div className="conversation-context">
              <span
                className={`context-dot ${mode === "chat" ? "chat-dot" : ""}`}
              />
              {mode === "chat"
                ? "Each question starts fresh. Documents are not used."
                : document
                  ? `Grounded in ${document.source}`
                  : "Add a document to begin your conversation."}
            </div>
            <div
              className="message-scroll"
              tabIndex={0}
              role="log"
              aria-live="polite"
              aria-label="Messages"
            >
              {!messages.length && !asking ? (
                <div className="welcome">
                  <div className="glass-orbit" aria-hidden="true">
                    <span className="orbit-ring one" />
                    <span className="orbit-ring two" />
                    <span className="orbit-ring three" />
                    <div className="orbit-core">
                      <Icon name="spark" size={32} />
                    </div>
                    <span className="orbit-dot" />
                  </div>
                  <span className="eyebrow">
                    {mode === "documents"
                      ? "GOOD QUESTIONS START HERE"
                      : "A LITTLE ROOM TO THINK"}
                  </span>
                  <h2>
                    {mode === "documents" ? (
                      <>
                        Your knowledge,
                        <br />
                        <em>in conversation.</em>
                      </>
                    ) : (
                      <>
                        A thought partner,
                        <br />
                        <em>on your terms.</em>
                      </>
                    )}
                  </h2>
                  <p>
                    {mode === "documents"
                      ? "Upload a document, ask what’s on your mind, and follow every answer back to its source."
                      : "Explore an idea with your local assistant. This mode does not use your document or provide source citations."}
                  </p>
                  <div className="welcome-rule" />
                  <span className="welcome-caption">
                    {mode === "documents"
                      ? "Read between the lines. Then check them."
                      : "Start with a question. See where it goes."}
                  </span>
                </div>
              ) : (
                messages.map((message) => (
                  <article
                    key={message.id}
                    className={`message ${message.role}`}
                  >
                    <div className="message-avatar">
                      {message.role === "assistant" ? (
                        <Logo small />
                      ) : (
                        <span>Y</span>
                      )}
                    </div>
                    <div className="message-content">
                      <div className="message-label">
                        {message.role === "assistant" ? "Folio" : "You"}
                        {message.found === false && (
                          <span className="not-found">
                            Not found in document
                          </span>
                        )}
                      </div>
                      <p>{message.text}</p>
                      {message.sources.length > 0 && (
                        <button
                          className="source-button"
                          onClick={() => showEvidence(message.id)}
                        >
                          <Icon name="book" size={15} />
                          {message.citations.length
                            ? `${message.citations.length} cited ${message.citations.length === 1 ? "passage" : "passages"}`
                            : "Review retrieved passages"}
                          <Icon name="chevron" size={13} />
                        </button>
                      )}
                    </div>
                  </article>
                ))
              )}
              {asking && (
                <div className="thinking" role="status">
                  <Logo small />
                  <span>
                    {mode === "documents"
                      ? "Finding the thread in your document"
                      : "A little thought in progress"}
                    <span className="thinking-dots">…</span>
                  </span>
                </div>
              )}
              <div ref={bottom} />
            </div>
            <div className="composer-area">
              {notice && (
                <p className="notice" role="status">
                  <Icon name="check" size={15} />
                  {notice}
                </p>
              )}
              {error && (
                <div className="error-notice" role="alert">
                  <Icon name="info" size={17} />
                  <span>{error}</span>
                  <button
                    className="icon-button"
                    aria-label="Dismiss error"
                    onClick={() => setError(null)}
                  >
                    <Icon name="close" size={16} />
                  </button>
                </div>
              )}
              {!messages.length && mode === "documents" && (
                <div className="suggestions" aria-label="Suggested questions">
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={suggestion}
                      disabled={busy}
                      onClick={() => {
                        setInput(suggestion);
                        question.current?.focus();
                      }}
                    >
                      {index === 0 && <Icon name="spark" size={13} />}
                      <span>{suggestion}</span>
                    </button>
                  ))}
                </div>
              )}
              <form className="composer" onSubmit={(event) => void ask(event)}>
                <label htmlFor="question" className="composer-label">
                  {mode === "documents" ? "Ask your document" : "Ask Folio"}
                </label>
                <textarea
                  id="question"
                  ref={question}
                  rows={2}
                  maxLength={2000}
                  value={input}
                  disabled={busy}
                  placeholder={
                    mode === "documents"
                      ? document
                        ? "What would you like to understand?"
                        : "Upload a document to start exploring…"
                      : "What’s on your mind?"
                  }
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                />
                <div className="composer-bottom">
                  <span>
                    <span className="composer-spark">
                      <Icon name="spark" size={13} />
                    </span>
                    {mode === "documents"
                      ? "Answers with a paper trail"
                      : "Powered by your local model"}
                  </span>
                  <span className="composer-controls">
                    <span className="character-count">{input.length}/2000</span>
                    <button
                      className="send-button"
                      aria-label="Send question"
                      disabled={
                        busy ||
                        loading ||
                        !input.trim() ||
                        (mode === "documents" && !document)
                      }
                      type="submit"
                    >
                      {asking ? (
                        <span className="loader" />
                      ) : (
                        <Icon name="arrow" size={21} />
                      )}
                    </button>
                  </span>
                </div>
              </form>
              <p className="composer-footnote">
                A helpful starting point, not the final word. Check important
                details.
              </p>
            </div>
          </section>
          <Evidence
            sources={evidence?.sources || []}
            citations={evidence?.citations || []}
          />
        </div>
        <footer className="app-footer">
          <span>
            <Logo small />
            Thoughtfully connected. Locally grounded.
          </span>
          <span>
            Built by{" "}
            <a href="https://yousan-nim.com" target="_blank" rel="noreferrer">
              Pongchanok Nuamteam
              <Icon name="link" size={12} />
            </a>
          </span>
        </footer>
      </main>
      <dialog
        className="about-dialog glass"
        aria-labelledby="about-title"
        ref={info}
        onClick={(event) => {
          if (event.target === event.currentTarget) info.current?.close();
        }}
      >
        <button
          className="icon-button dialog-close"
          aria-label="Close about"
          onClick={() => info.current?.close()}
        >
          <Icon name="close" />
        </button>
        <Logo />
        <p className="eyebrow">A LITTLE CONTEXT</p>
        <h2 id="about-title">
          Meet your knowledge,
          <br />
          on a clearer day.
        </h2>
        <p>
          Folio turns one document into a conversation. Upload a PDF, text or
          Markdown file and ask a question. The answer comes with the original
          passages so you can check it yourself.
        </p>
        <p>
          Scanned pages can be read with Thai and English OCR. Uploads are
          limited to 1 MiB, 50 PDF pages, and 5 pages requiring OCR. Uploading a
          new document replaces the previous one.
        </p>
        <p>
          Free chat talks to the local model without searching your document.
          History is displayed in this tab, but earlier messages are not sent as
          context. Each question is answered independently. History is cleared
          when you reload.
        </p>
        <button
          className="button primary"
          onClick={() => info.current?.close()}
        >
          Let’s explore <Icon name="chevron" size={16} />
        </button>
      </dialog>
    </div>
  );
}
