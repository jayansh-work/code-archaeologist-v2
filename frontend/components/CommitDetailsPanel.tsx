"use client";

import { changeTypeLabel, copyText, formatCount, formatRelative, formatTimestamp } from "@/lib/format";
import type { CommitEvidence } from "@/lib/types";

type CommitDetailsPanelProps = {
  commit: CommitEvidence | null;
  onAsk: (commit: CommitEvidence) => void;
  onAskFile: (path: string) => void;
  onSelectFile: (path: string) => void;
};

export default function CommitDetailsPanel({
  commit,
  onAsk,
  onAskFile,
  onSelectFile,
}: CommitDetailsPanelProps) {
  if (!commit) {
    return (
      <aside className="details-panel">
        <h3>Commit details</h3>
        <p className="empty">Select a commit in the graph to inspect files and change statistics.</p>
      </aside>
    );
  }

  return (
    <aside className="details-panel" aria-live="polite">
      <h3>Commit details</h3>
      <p>
        <span className="hash">{commit.short_hash}</span>
      </p>
      <p className="commit-msg">{commit.message}</p>
      <div className="meta-grid">
        <div>
          Author <span>{commit.author}</span>
        </div>
        <div>
          When{" "}
          <span>
            {formatRelative(commit.timestamp)}
            {formatRelative(commit.timestamp) !== formatTimestamp(commit.timestamp) ? (
              <span className="exact-time"> · {formatTimestamp(commit.timestamp)}</span>
            ) : null}
          </span>
        </div>
        <div>
          Hash <span className="full-hash">{commit.hash}</span>
        </div>
      </div>
      <p>
        {commit.files.length} {commit.files.length === 1 ? "file" : "files"} ·{" "}
        <span className="add">+{formatCount(commit.additions)}</span>{" "}
        <span className="del">-{formatCount(commit.deletions)}</span>
      </p>
      <div className="inline-actions">
        <button
          className="ghost-btn"
          type="button"
          onClick={() => {
            void copyText(commit.hash);
          }}
        >
          Copy hash
        </button>
        <button className="ghost-btn" type="button" onClick={() => onAsk(commit)}>
          Ask AI about this commit
        </button>
      </div>
      <table className="file-table">
        <caption className="status-live">Changed files</caption>
        <thead>
          <tr>
            <th scope="col">Type</th>
            <th scope="col">File</th>
            <th scope="col">Changes</th>
          </tr>
        </thead>
        <tbody>
          {commit.files.length === 0 ? (
            <tr>
              <td colSpan={3}>No file-level changes were recorded for this commit.</td>
            </tr>
          ) : (
            commit.files.map((file) => (
              <tr key={file.path}>
                <td className="kind">{changeTypeLabel(file.change_type)}</td>
                <td>
                  <button className="link-btn file-path" type="button" onClick={() => onSelectFile(file.path)}>
                    {file.path}
                  </button>
                  <button className="link-btn" type="button" onClick={() => onAskFile(file.path)}>
                    Ask AI about this file
                  </button>
                </td>
                <td className="churn">
                  <span className="add">+{formatCount(file.additions)}</span>{" "}
                  <span className="del">-{formatCount(file.deletions)}</span>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </aside>
  );
}
