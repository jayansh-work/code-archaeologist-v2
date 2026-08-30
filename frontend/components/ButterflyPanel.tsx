"use client";

import { computeButterfly } from "@/lib/butterfly";
import { formatCount } from "@/lib/format";
import type { CommitEvidence } from "@/lib/types";

type ButterflyPanelProps = {
  commit: CommitEvidence | null;
  commits: CommitEvidence[];
  onSelectHash: (hash: string) => void;
  onSelectFile: (path: string) => void;
  onAsk: (commit: CommitEvidence) => void;
};

export default function ButterflyPanel({
  commit,
  commits,
  onSelectHash,
  onSelectFile,
  onAsk,
}: ButterflyPanelProps) {
  if (!commit) {
    return (
      <aside className="details-panel butterfly-panel">
        <h3>Butterfly effect</h3>
        <p className="empty">
          Select a commit in the flowchart to trace which later work reused the same files.
        </p>
      </aside>
    );
  }

  const trace = computeButterfly(commits, commit);
  const wings = trace.files.slice(0, 5);

  return (
    <aside className="details-panel butterfly-panel" aria-live="polite">
      <h3>Butterfly effect</h3>
      <p>
        <span className="hash">{commit.short_hash}</span>
      </p>
      <p className="commit-msg">{commit.message}</p>
      {wings.length === 0 ? (
        <p className="empty">
          This commit recorded no file-level changes, so a butterfly effect cannot be traced.
        </p>
      ) : (
        <>
          <p className="form-hint">File wings — later commits that reuse these paths</p>
          <div className="related-files">
            {wings.map((path) => (
              <button key={path} className="chip" type="button" onClick={() => onSelectFile(path)}>
                {path}
              </button>
            ))}
            {trace.files.length > wings.length ? (
              <span className="form-hint">+{trace.files.length - wings.length} more</span>
            ) : null}
          </div>
          <ButterflyGroup
            title="Upstream"
            empty="No earlier analyzed commit touched these files."
            links={trace.upstream}
            onSelectHash={onSelectHash}
          />
          <ButterflyGroup
            title="Downstream"
            empty="No later analyzed commit reused these files."
            links={trace.downstream}
            onSelectHash={onSelectHash}
          />
        </>
      )}
      <div className="inline-actions">
        <button className="ghost-btn" type="button" onClick={() => onAsk(commit)}>
          Ask AI about this butterfly
        </button>
      </div>
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
