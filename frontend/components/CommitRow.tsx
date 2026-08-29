"use client";

import { changeTypeLabel, formatCount, formatTimestamp } from "@/lib/format";
import type { CommitEvidence } from "@/lib/types";

type CommitRowProps = {
  commit: CommitEvidence;
  open: boolean;
  onToggle: () => void;
};

export default function CommitRow({ commit, open, onToggle }: CommitRowProps) {
  const panelId = `commit-${commit.hash}`;
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
              When <span>{formatTimestamp(commit.timestamp)}</span>
            </div>
            <div>
              Hash <span className="full-hash">{commit.hash}</span>
            </div>
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
                    <td className="file-path">{file.path}</td>
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
