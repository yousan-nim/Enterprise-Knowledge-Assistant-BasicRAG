import { Source } from "@/lib/api";
import { Icon } from "./icon";
export function Evidence({
  sources,
  citations,
}: {
  sources: Source[];
  citations: string[];
}) {
  return (
    <aside
      className="evidence-panel glass"
      id="evidence"
      aria-label="Sources and evidence"
      tabIndex={-1}
    >
      <div className="panel-heading">
        <span className="eyebrow">THE PAPER TRAIL</span>
        <span className="count">
          {sources.length.toString().padStart(2, "0")}
        </span>
      </div>
      <h2>Grounded in your words.</h2>
      <p className="muted small">
        The passages behind the answer. Always worth a closer look.
      </p>
      {!sources.length ? (
        <div className="evidence-empty">
          <div className="outline-icon">
            <Icon name="book" size={27} />
          </div>
          <h3>A place for the proof.</h3>
          <p>
            Your document excerpts will appear here after you ask a question.
          </p>
          <span className="fine-line" />
        </div>
      ) : (
        <div className="source-list">
          {sources.map((source, index) => (
            <details
              className="source-card"
              key={`${source.id}-${index}`}
              open={index === 0}
            >
              <summary>
                <span className="source-number">{index + 1}</span>
                <span className="source-summary">
                  <strong title={source.source}>{source.source}</strong>
                  <span>
                    Page {source.page} <span aria-hidden="true">·</span>{" "}
                    {citations.includes(source.id)
                      ? "Cited in answer"
                      : "Retrieved passage"}
                  </span>
                </span>
                <Icon name="chevron" size={16} />
              </summary>
              <div className="source-body">
                <blockquote>{source.text}</blockquote>
                <div className="source-meta">
                  <span>
                    {source.extraction_method === "ocr"
                      ? "Read with OCR"
                      : "Extracted text"}
                  </span>
                  <span title="Cosine similarity is a retrieval ranking, not confidence in the answer.">
                    Similarity {source.score.toFixed(2)}
                  </span>
                </div>
              </div>
            </details>
          ))}
        </div>
      )}
      <div className="evidence-foot">
        <Icon name="info" size={15} />
        <span>
          Citations help you check an answer. They don’t guarantee it’s correct.
        </span>
      </div>
    </aside>
  );
}
