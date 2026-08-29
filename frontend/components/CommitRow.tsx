"use client";

import { useState } from "react";

import { changeTypeLabel, copyText, formatCount, formatRelative, formatTimestamp } from "@/lib/format";
import type { CommitEvidence } from "@/lib/types";

type CommitRowProps = {
  commit: CommitEvidence;
  open: boolean;
  onToggle: () => void;
  onAsk: () => void;
  onAskFile: (path: string) => void;
  onSelectFile: (path: string) => void;
};

export default function CommitRow({
  commit,
  open,
  onToggle,
  onAsk,
  onAskFile,
  onSelectFile,
}: CommitRowProps) {
  const panelId = `commit-${commit.hash}`;
  const [copied, setCopied] = useState(false);

  return (
    <li className={open ? "commit-row is-open" : "commit-row"}>
      <button
        type="button"
        className="commit-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <span className="rail" aria-hidden="true" />
        <span className="hash commit-hash-col">{commit.short_hash}</span>
        <span className="commit-msg">{commit.message}</span>
        <span className="commit-side">
          {commit.files.length} {commit.files.length === 1 ? "file" : "files"}
          <br />
          <span className="add">+{formatCount(commit.additions)}</span>{" "}
          <span className="del">-{formatCount(commit.deletions)}</span>
        </span>
      </button>
      {open ? (
        <div className="commit-detail" id={panelId}>
          <div className="meta-grid">
            <div>
              Author <span>{commit.author}</span>
            </div>
            <div>
              When{" "}
              <span title={formatTimestamp(commit.timestamp)}>{formatRelative(commit.timestamp)}</span>
            </div>
            <div>
              Hash <span className="full-hash">{commit.hash}</span>
            </div>
          </div>
          <div className="inline-actions">
            <button
              className="ghost-btn"
              type="button"
              onClick={() => {
                void copyText(commit.hash).then((ok) => {
                  setCopied(ok);
                  window.setTimeout(() => setCopied(false), 1200);
                });
              }}
            >
              {copied ? "Copied" : "Copy hash"}
            </button>
            <button className="ghost-btn" type="button" onClick={onAsk}>
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
        </div>
      ) : null}
    </li>
  );
}
