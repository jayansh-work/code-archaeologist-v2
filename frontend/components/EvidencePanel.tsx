"use client";

import CitedText from "@/components/CitedText";
import { formatCount, formatTimestamp } from "@/lib/format";
import type { QueryResponse } from "@/lib/types";

type EvidencePanelProps = {
  result: QueryResponse;
  loading: boolean;
  onSelectHash: (hash: string) => void;
  onSelectFile: (path: string) => void;
  onAsk: (question: string) => void;
  onRetry: () => void;
};

export default function EvidencePanel({
  result,
  loading,
  onSelectHash,
  onSelectFile,
  onAsk,
  onRetry,
}: EvidencePanelProps) {
  const unavailable = result.mode === "ai-unavailable" && !result.ai_used;
  const unavailableTitle =
    result.unavailable_reason === "not_configured"
      ? "AI investigation is not configured."
      : result.unavailable_reason === "invalid_key"
        ? "Gemini rejected the API key."
        : "AI investigation is temporarily unavailable.";
  const unavailableBody =
    result.unavailable_reason === "not_configured"
      ? "Paste GEMINI_API_KEY into backend/.env, then retry. Restart is not required. Repository evidence remains available below."
      : result.unavailable_reason === "invalid_key"
        ? "Check GEMINI_API_KEY in backend/.env. Repository evidence remains available below."
        : "Repository evidence remains available below.";

  return (
    <section className="finding" aria-labelledby="finding-heading">
      <h2 id="finding-heading" className="section-title">
        Finding
      </h2>
      {unavailable ? (
        <div className="error-box" role="status">
          <p>{unavailableTitle}</p>
          <p>{unavailableBody}</p>
          <button className="ghost-btn" type="button" onClick={onRetry} disabled={loading}>
            Retry
          </button>
        </div>
      ) : (
        <CitedText text={result.answer} onSelectHash={onSelectHash} />
      )}

      {unavailable && result.retrieval_summary ? (
        <>
          <h2 className="section-title">Retrieved Git evidence</h2>
          <CitedText text={result.retrieval_summary} onSelectHash={onSelectHash} />
        </>
      ) : null}

      {!unavailable && result.confidence ? (
        <>
          <h2 className="section-title">Confidence</h2>
          <p className="confidence">
            <strong>{result.confidence}</strong>
            {result.confidence === "low" ? " — evidence in the analyzed window is limited." : null}
          </p>
        </>
      ) : null}

      {!unavailable && result.why ? (
        <>
          <h2 className="section-title">Why</h2>
          <p>{result.why}</p>
        </>
      ) : null}

      {result.related_files.length > 0 ? (
        <>
          <h2 className="section-title">Related files</h2>
          <div className="related-files">
            {result.related_files.map((path) => (
              <button key={path} className="chip" type="button" onClick={() => onSelectFile(path)}>
                {path}
              </button>
            ))}
          </div>
        </>
      ) : null}

      <h2 className="section-title">Evidence</h2>
      {result.evidence.length === 0 ? (
        <p className="empty">
          No matching commits found. Try a commit message, file path, author, or hash.
        </p>
      ) : (
        <ul className="evidence-list">
          {result.evidence.map((item) => (
            <li key={item.hash}>
              <button type="button" onClick={() => onSelectHash(item.hash)}>
                <div className="ev-meta">
                  <span className="hash">{item.short_hash}</span>
                  <span>{item.author}</span>
                  <span>{formatTimestamp(item.timestamp)}</span>
                  <span className="churn">
                    <span className="add">+{formatCount(item.additions)}</span>{" "}
                    <span className="del">-{formatCount(item.deletions)}</span>
                  </span>
                </div>
                <p className="commit-msg">{item.message}</p>
                {item.files.length > 0 ? (
                  <p className="file-path">{item.files.slice(0, 4).join("  ·  ")}</p>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      )}

      {result.follow_ups.length > 0 ? (
        <>
          <h2 className="section-title">Follow-up suggestions</h2>
          <div className="suggestions">
            {result.follow_ups.map((item) => (
              <button key={item} className="chip" type="button" disabled={loading} onClick={() => onAsk(item)}>
                {item}
              </button>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
