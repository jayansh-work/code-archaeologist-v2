"use client";

import InlineFinding from "@/components/InlineFinding";
import { BUTTERFLY_CAVEAT, computeButterfly } from "@/lib/butterfly";
import { formatCount } from "@/lib/format";
import {
  butterflyQuestion,
  butterflySlot,
  fileQuestion,
  fileSlot,
  type InlineAskState,
} from "@/lib/inlineAsk";
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
        A small change can spread. If later saved changes edit the same files, the original change
        did not stay isolated — its area of the codebase continued evolving. {BUTTERFLY_CAVEAT}
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
              const fileAsk = asks[explainSlot];
              const prompt = fileQuestion(path);
              return (
                <div key={path} className="wing-row">
                  <div className="wing-head">
                    <button className="chip" type="button" onClick={() => onSelectFile(path)}>
                      {path}
                    </button>
                    <button
                      className="link-btn"
                      type="button"
                      disabled={fileAsk?.status === "loading"}
                      onClick={() => onAsk(explainSlot, prompt, commit, path)}
                    >
                      {fileAsk?.status === "loading" ? "Asking AI…" : "Explain this file"}
                    </button>
                  </div>
                  <InlineFinding
                    ask={fileAsk}
                    onSelectHash={onSelectHash}
                    onRetry={() =>
                      onAsk(explainSlot, fileAsk?.question || prompt, commit, path)
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
            title="After this change"
            empty="No later analyzed commit edited these files again in this window."
            links={trace.after}
            emphasis
            onSelectHash={onSelectHash}
          />
          <ButterflyGroup
            title="Before this change"
            empty="No earlier analyzed commit had already edited these files."
            links={trace.before}
            onSelectHash={onSelectHash}
          />
        </>
      )}
      <div className="inline-actions">
        <button
          className="ghost-btn"
          type="button"
          disabled={ask?.status === "loading"}
          onClick={() => onAsk(slot, butterflyQuestion(commit.short_hash), commit)}
        >
          {ask?.status === "loading" ? "Asking AI…" : "Ask AI about this butterfly"}
        </button>
      </div>
      <InlineFinding
        ask={ask}
        onSelectHash={onSelectHash}
        onRetry={() =>
          onAsk(slot, ask?.question || butterflyQuestion(commit.short_hash), commit)
        }
      />
    </aside>
  );
}

function ButterflyGroup({
  title,
  empty,
  links,
  emphasis = false,
  onSelectHash,
}: {
  title: string;
  empty: string;
  links: { commit: CommitEvidence; shared: string[] }[];
  emphasis?: boolean;
  onSelectHash: (hash: string) => void;
}) {
  return (
    <div className={emphasis ? "butterfly-group is-primary" : "butterfly-group"}>
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
