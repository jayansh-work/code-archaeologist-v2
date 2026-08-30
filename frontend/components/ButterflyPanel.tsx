"use client";

import InlineFinding from "@/components/InlineFinding";
import { computeButterfly } from "@/lib/butterfly";
import { formatCount } from "@/lib/format";
import { butterflySlot, fileSlot, type InlineAskState } from "@/lib/inlineAsk";
import type { CommitEvidence } from "@/lib/types";

type ButterflyPanelProps = {
  commit: CommitEvidence | null;
  commits: CommitEvidence[];
  asks: Record<string, InlineAskState>;
  onSelectHash: (hash: string) => void;
  onSelectFile: (path: string) => void;
  onAsk: (slot: string, question: string, commit: CommitEvidence, file?: string) => void;
};

export default function ButterflyPanel({
  commit,
  commits,
  asks,
  onSelectHash,
  onSelectFile,
  onAsk,
}: ButterflyPanelProps) {
  if (!commit) {
    return (
      <aside className="details-panel butterfly-panel">
        <h3>Butterfly effect</h3>
        <p className="empty">
          Pick a commit on the flowchart. We will show whether that change stayed put or showed up
          again later.
        </p>
      </aside>
    );
  }

  const trace = computeButterfly(commits, commit);
  const wings = trace.files.slice(0, 5);
  const slot = butterflySlot(commit.hash);
  const ask = asks[slot];

  return (
    <aside className="details-panel butterfly-panel" aria-live="polite">
      <h3>Butterfly effect</h3>
      <p className="butterfly-plain">
        A small change can spread. If later commits edit the same files, the original change did not
        stay in one place — it rippled forward. This is Git file history, not a guess about bugs or
        why someone made the change.
      </p>
      <p>
        <span className="hash">{commit.short_hash}</span>
      </p>
      <p className="commit-msg">{commit.message}</p>
      {wings.length === 0 ? (
        <p className="empty">
          This commit did not record any changed files, so there is nothing to follow.
        </p>
      ) : (
        <>
          <h4>Files this commit touched</h4>
          <div className="wing-list">
            {wings.map((path) => {
              const explainSlot = fileSlot(commit.hash, path);
              return (
                <div key={path} className="wing-row">
                  <div className="wing-head">
                    <button className="chip" type="button" onClick={() => onSelectFile(path)}>
                      {path}
                    </button>
                    <button
                      className="link-btn"
                      type="button"
                      onClick={() =>
                        onAsk(
                          explainSlot,
                          `Explain the file ${path} in plain English. What is it, and how did it change in the analyzed Git history?`,
                          commit,
                          path,
                        )
                      }
                    >
                      Explain this file
                    </button>
                  </div>
                  <InlineFinding
                    ask={asks[explainSlot]}
                    onSelectHash={onSelectHash}
                    onRetry={() =>
                      onAsk(
                        explainSlot,
                        asks[explainSlot]?.question ??
                          `Explain the file ${path} in plain English. What is it, and how did it change in the analyzed Git history?`,
                        commit,
                        path,
                      )
                    }
                  />
                </div>
              );
            })}
            {trace.files.length > wings.length ? (
              <span className="form-hint">+{trace.files.length - wings.length} more in commit details</span>
            ) : null}
          </div>
          <ButterflyGroup
            title="Before this commit"
            empty="No earlier analyzed commit had already edited these files."
            links={trace.upstream}
            onSelectHash={onSelectHash}
          />
          <ButterflyGroup
            title="After this commit"
            empty="No later analyzed commit edited these files again."
            links={trace.downstream}
            onSelectHash={onSelectHash}
          />
        </>
      )}
      <div className="inline-actions">
        <button
          className="ghost-btn"
          type="button"
          disabled={ask?.status === "loading"}
          onClick={() =>
            onAsk(
              slot,
              `In plain English, explain the butterfly effect of commit ${commit.short_hash}. Which later work reused the same files?`,
              commit,
            )
          }
        >
          {ask?.status === "loading" ? "Asking AI…" : "Ask AI about this butterfly"}
        </button>
      </div>
      <InlineFinding
        ask={ask}
        onSelectHash={onSelectHash}
        onRetry={() =>
          onAsk(
            slot,
            ask?.question ??
              `In plain English, explain the butterfly effect of commit ${commit.short_hash}. Which later work reused the same files?`,
            commit,
          )
        }
      />
    </aside>
  );
}

function ButterflyGroup({
  title,
  empty,
  links,
  onSelectHash,
}: {
  title: string;
  empty: string;
  links: { commit: CommitEvidence; shared: string[] }[];
  onSelectHash: (hash: string) => void;
}) {
  return (
    <div className="butterfly-group">
      <h4>
        {title}
        {links.length > 0 ? <span className="form-hint"> ({formatCount(links.length)})</span> : null}
      </h4>
      {links.length === 0 ? (
        <p className="empty">{empty}</p>
      ) : (
        <ul className="butterfly-list">
          {links.map((item) => (
            <li key={item.commit.hash}>
              <button type="button" onClick={() => onSelectHash(item.commit.hash)}>
                <span className="hash">{item.commit.short_hash}</span>
                <span className="butterfly-msg">{item.commit.message}</span>
                <span className="file-path">{item.shared.slice(0, 3).join(" · ")}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
