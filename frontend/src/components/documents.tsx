import { useRef, useState } from "react";
import type { DocumentInfo } from "@/lib/api";
import { Icon } from "./icon";
type Props = {
  document: DocumentInfo | null;
  loading: boolean;
  busy: boolean;
  uploading: boolean;
  deleting: boolean;
  connected: boolean | null;
  onFile: (file: File) => void;
  onSample: () => void;
  onDelete: () => void;
  onRefresh: () => void;
  pendingFile: File | null;
  onConfirmUpload: () => void;
  onCancelUpload: () => void;
};
export function Documents(p: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  return (
    <aside className="document-panel glass" aria-label="Document library">
      <div className="panel-heading">
        <span className="eyebrow">YOUR CONTEXT</span>
        <Icon name="layers" size={18} />
      </div>
      <h2>
        A small library.
        <br />A clearer picture.
      </h2>
      <p className="muted small">
        Start with one document.
        <br />
        We’ll help you connect the dots.
      </p>
      <label
        className={`upload-zone ${dragging ? "dragging" : ""} ${p.busy ? "disabled" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!p.busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!p.busy && event.dataTransfer.files[0])
            p.onFile(event.dataTransfer.files[0]);
        }}
      >
        <input
          ref={input}
          type="file"
          className="visually-hidden"
          accept=".pdf,.txt,.md"
          disabled={p.busy || p.loading}
          aria-label="Upload a PDF, TXT or Markdown document"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) p.onFile(file);
            event.target.value = "";
          }}
        />
        <span className={`upload-icon ${p.uploading ? "spinning" : ""}`}>
          <Icon name={p.uploading ? "refresh" : "upload"} size={24} />
        </span>
        <strong>
          {p.uploading
            ? "Making sense of your file…"
            : "Drop a little knowledge."}
        </strong>
        <span>
          {p.uploading
            ? "Reading, indexing, getting ready."
            : "Drop a file here, or click to browse"}
        </span>
        <small>
          PDF, TXT, MD <span aria-hidden="true">·</span> up to 1 MiB
        </small>
      </label>
      {p.pendingFile && (
        <div className="inline-confirm" role="alert">
          <strong>Replace your document?</strong>
          <p>
            <b>{p.pendingFile.name}</b> will replace the indexed document. Your
            conversation will be cleared after it succeeds.
          </p>
          <div className="button-row">
            <button
              className="button primary compact"
              onClick={p.onConfirmUpload}
              disabled={p.busy}
            >
              Replace
            </button>
            <button
              className="button subtle compact"
              onClick={p.onCancelUpload}
              disabled={p.busy}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <div className="library-label">
        <span className="eyebrow">INDEXED DOCUMENT</span>
        <button
          className="icon-button"
          aria-label="Refresh document list"
          onClick={p.onRefresh}
          disabled={p.busy || p.loading}
        >
          <Icon name="refresh" size={16} />
        </button>
      </div>
      {p.loading ? (
        <p className="small muted" role="status">
          Opening your library…
        </p>
      ) : p.document ? (
        <div className="document-card">
          <span className="file-icon">
            <Icon name="file" />
          </span>
          <div className="file-description">
            <strong title={p.document.source}>{p.document.source}</strong>
            <span>
              {p.document.chunks} passages <span aria-hidden="true">·</span>{" "}
              Ready to explore
            </span>
          </div>
          <button
            className="icon-button danger"
            aria-label={`Remove ${p.document.source}`}
            onClick={() => setConfirmDelete(true)}
            disabled={p.busy}
          >
            <Icon name="trash" size={17} />
          </button>
        </div>
      ) : (
        <div className="no-document">
          <span className="tiny-dot" />
          <span>
            {p.connected === false
              ? "Library unavailable. Try refresh."
              : "Your next good question starts here."}
          </span>
        </div>
      )}
      {confirmDelete && p.document && (
        <div className="inline-confirm">
          <strong>Remove this document?</strong>
          <p>
            Its indexed passages will be deleted. You can upload it again
            anytime.
          </p>
          <div className="button-row">
            <button
              className="button destructive compact"
              onClick={() => {
                setConfirmDelete(false);
                p.onDelete();
              }}
              disabled={p.busy}
            >
              Remove
            </button>
            <button
              className="button subtle compact"
              onClick={() => setConfirmDelete(false)}
              disabled={p.busy}
            >
              Keep it
            </button>
          </div>
        </div>
      )}
      <div className="sample-card">
        <span className="eyebrow">JUST EXPLORING?</span>
        <p>Take a company handbook for a spin.</p>
        <button
          className="text-button"
          onClick={p.onSample}
          disabled={p.busy || p.loading}
        >
          Try the sample document <Icon name="chevron" size={16} />
        </button>
      </div>
      <div className="local-note">
        <Icon name="shield" size={17} />
        <span>Local models. Your own workspace.</span>
      </div>
    </aside>
  );
}
