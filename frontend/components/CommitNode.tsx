"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

import { formatCount, formatShortDate } from "@/lib/format";
import type { CommitEvidence } from "@/lib/types";

export type CommitNodeData = {
  commit: CommitEvidence;
  selected: boolean;
  isLarge: boolean;
  onSelect: () => void;
};

export type CommitFlowNode = Node<CommitNodeData, "commit">;

export default function CommitNode({ data }: NodeProps<CommitFlowNode>) {
  const { commit, selected, isLarge, onSelect } = data;
  const className = [
    "commit-node",
    selected ? "is-selected" : "",
    isLarge ? "is-large" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={className}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      aria-label={`${commit.short_hash} ${commit.message}`}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="ev-meta">
        <span className="hash">{commit.short_hash}</span>
        {isLarge ? (
          <span className="large-mark" title="Largest change in this window">
            Large
          </span>
        ) : null}
        <span>
          <span className="add">+{formatCount(commit.additions)}</span>{" "}
          <span className="del">-{formatCount(commit.deletions)}</span>
        </span>
      </div>
      <p className="node-msg" title={commit.message}>
        {commit.message}
      </p>
      <div className="ev-meta">
        <span>{commit.author}</span>
        <span>{formatShortDate(commit.timestamp)}</span>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
