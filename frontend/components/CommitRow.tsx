"use client";

import { useState } from "react";

import InlineFinding from "@/components/InlineFinding";
import { changeTypeLabel, copyText, formatCount, formatRelative, formatTimestamp } from "@/lib/format";
import { commitQuestion, commitSlot, fileQuestion, fileSlot, type InlineAskState } from "@/lib/inlineAsk";
import type { CommitEvidence } from "@/lib/types";

type CommitRowProps = {
  commit: CommitEvidence;
  open: boolean;
  asks: Record<string, InlineAskState>;
  onToggle: () => void;
  onAsk: (slot: string, question: string, commit: CommitEvidence, file?: string) => void;
  onSelectFile: (path: string) => void;
  onSelectHash: (hash: string) => void;
};

export default function CommitRow({
  commit,
  open,
  asks,
  onToggle,
  onAsk,
  onSelectFile,
  onSelectHash,
}: CommitRowProps) {
  const panelId = `commit-${commit.hash}`;
  const [copied, setCopied] = useState(false);
  const slot = commitSlot(commit.hash);
  const ask = asks[slot];
  const question = commitQuestion(commit.short_hash);

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
            <button
              className="ghost-btn"
              type="button"
              disabled={ask?.status === "loading"}
              onClick={() => onAsk(slot, question, commit)}
            >
              {ask?.status === "loading" ? "Asking AI…" : "Ask AI about this commit"}
            </button>
          </div>
          <InlineFinding
            ask={ask}
            onSelectHash={onSelectHash}
            onRetry={() => onAsk(slot, ask?.question || question, commit)}
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
                  const fileAsk = asks[explainSlot];
                  const filePrompt = fileQuestion(file.path);
                  return (
                    <FileRows
                      key={file.path}
                      commit={commit}
                      path={file.path}
                      changeType={file.change_type}
                      additions={file.additions}
                      deletions={file.deletions}
                      slot={explainSlot}
                      ask={fileAsk}
                      question={filePrompt}
                      onAsk={onAsk}
                      onSelectFile={onSelectFile}
                      onSelectHash={onSelectHash}
                    />
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </li>
  );
}

function FileRows({
  commit,
  path,
  changeType,
  additions,
  deletions,
  slot,
  ask,
  question,
  onAsk,
  onSelectFile,
  onSelectHash,
}: {
  commit: CommitEvidence;
  path: string;
  changeType: string | null;
  additions: number;
  deletions: number;
  slot: string;
  ask: InlineAskState | undefined;
  question: string;
  onAsk: (slot: string, question: string, commit: CommitEvidence, file?: string) => void;
  onSelectFile: (path: string) => void;
  onSelectHash: (hash: string) => void;
}) {
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
            onClick={() => onAsk(slot, question, commit, path)}
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
              onRetry={() => onAsk(slot, ask.question || question, commit, path)}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}
