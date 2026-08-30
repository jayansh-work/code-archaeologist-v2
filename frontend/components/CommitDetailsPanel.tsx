"use client";

import InlineFinding from "@/components/InlineFinding";
import { changeTypeLabel, copyText, formatCount, formatRelative, formatTimestamp } from "@/lib/format";
import { commitSlot, fileSlot, type InlineAskState } from "@/lib/inlineAsk";
import type { CommitEvidence } from "@/lib/types";

type CommitDetailsPanelProps = {
  commit: CommitEvidence | null;
  asks: Record<string, InlineAskState>;
  onAsk: (slot: string, question: string, commit: CommitEvidence, file?: string) => void;
  onSelectFile: (path: string) => void;
  onSelectHash: (hash: string) => void;
};

export default function CommitDetailsPanel({
  commit,
  asks,
  onAsk,
  onSelectFile,
  onSelectHash,
}: CommitDetailsPanelProps) {
  if (!commit) {
    return (
      <aside className="details-panel">
        <h3>Commit details</h3>
        <p className="empty">Select a commit in the graph to inspect files and change statistics.</p>
      </aside>
    );
  }

  const askCommit = asks[commitSlot(commit.hash)];

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
        <button
          className="ghost-btn"
          type="button"
          disabled={askCommit?.status === "loading"}
          onClick={() =>
            onAsk(
              commitSlot(commit.hash),
              `In plain English, explain what changed in commit ${commit.short_hash} and what the Git history shows about those changes.`,
              commit,
            )
          }
        >
          {askCommit?.status === "loading" ? "Asking AI…" : "Ask AI about this commit"}
        </button>
      </div>
      <InlineFinding
        ask={askCommit}
        onSelectHash={onSelectHash}
        onRetry={() =>
          onAsk(
            commitSlot(commit.hash),
            askCommit?.question ??
              `In plain English, explain what changed in commit ${commit.short_hash} and what the Git history shows about those changes.`,
            commit,
          )
        }
      />
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
            commit.files.map((file) => {
              const explainSlot = fileSlot(commit.hash, file.path);
              return (
                <FileAskRows
                  key={file.path}
                  commit={commit}
                  path={file.path}
                  changeType={file.change_type}
                  additions={file.additions}
                  deletions={file.deletions}
                  ask={asks[explainSlot]}
                  onSelectFile={onSelectFile}
                  onSelectHash={onSelectHash}
                  onAsk={onAsk}
                />
              );
            })
          )}
        </tbody>
      </table>
    </aside>
  );
}

function FileAskRows({
  commit,
  path,
  changeType,
  additions,
  deletions,
  ask,
  onSelectFile,
  onSelectHash,
  onAsk,
}: {
  commit: CommitEvidence;
  path: string;
  changeType: string | null;
  additions: number;
  deletions: number;
  ask: InlineAskState | undefined;
  onSelectFile: (path: string) => void;
  onSelectHash: (hash: string) => void;
  onAsk: (slot: string, question: string, commit: CommitEvidence, file?: string) => void;
}) {
  const explainSlot = fileSlot(commit.hash, path);
  const question = `Explain the file ${path} in plain English. What is it, and how did it change in the analyzed Git history?`;
  return (
    <>
      <tr>
        <td className="kind">{changeTypeLabel(changeType)}</td>
        <td>
          <button className="link-btn file-path" type="button" onClick={() => onSelectFile(path)}>
            {path}
          </button>
          <button
            className="link-btn"
            type="button"
            disabled={ask?.status === "loading"}
            onClick={() => onAsk(explainSlot, question, commit, path)}
          >
            {ask?.status === "loading" ? "Asking AI…" : "Ask AI about this file"}
          </button>
        </td>
        <td className="churn">
          <span className="add">+{formatCount(additions)}</span>{" "}
          <span className="del">-{formatCount(deletions)}</span>
        </td>
      </tr>
      {ask ? (
        <tr>
          <td colSpan={3}>
            <InlineFinding
              ask={ask}
              onSelectHash={onSelectHash}
              onRetry={() => onAsk(explainSlot, ask.question || question, commit, path)}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}
