import { formatCount, formatTimestamp } from "@/lib/format";
import type { QueryResponse } from "@/lib/types";

type EvidencePanelProps = {
  result: QueryResponse;
  onSelectHash: (hash: string) => void;
};

export default function EvidencePanel({ result, onSelectHash }: EvidencePanelProps) {
  const modeLabel = result.ai_used ? "Grounded AI" : "Repository search";
  return (
    <section className="finding" aria-labelledby="finding-heading">
      <h2 id="finding-heading">Finding</h2>
      <p className="mode-tag">{modeLabel}</p>
      <p className="finding-body">{result.answer}</p>
      {result.evidence.length === 0 ? (
        <p className="empty">No matching commits found. Try a commit message, file path, author, or hash.</p>
      ) : (
        <>
          <h2>Evidence</h2>
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
        </>
      )}
    </section>
  );
}
