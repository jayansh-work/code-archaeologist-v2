"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import CommitNode, { type CommitFlowNode } from "@/components/CommitNode";
import type { CommitEvidence } from "@/lib/types";

const nodeTypes = { commit: CommitNode } as NodeTypes;

const NODE_W = 280;
const NODE_H = 108;
const GAP_Y = 28;

type EvolutionGraphProps = {
  commits: CommitEvidence[];
  selectedHash: string | null;
  onSelectHash: (hash: string) => void;
};

export default function EvolutionGraph(props: EvolutionGraphProps) {
  return (
    <div className="graph-shell">
      <ReactFlowProvider key={props.commits[0]?.hash ?? "empty"}>
        <GraphCanvas {...props} />
      </ReactFlowProvider>
    </div>
  );
}

function GraphCanvas({ commits, selectedHash, onSelectHash }: EvolutionGraphProps) {
  const { fitView } = useReactFlow();
  const chronologic = useMemo(() => [...commits].reverse(), [commits]);
  const churns = useMemo(
    () => chronologic.map((commit) => commit.additions + commit.deletions).sort((a, b) => a - b),
    [chronologic],
  );
  const largeThreshold = churns[Math.floor(churns.length * 0.8)] ?? 0;

  const nodes: CommitFlowNode[] = useMemo(
    () =>
      chronologic.map((commit, index) => ({
        id: commit.hash,
        type: "commit",
        position: { x: 36, y: index * (NODE_H + GAP_Y) },
        selected: selectedHash === commit.hash,
        data: {
          commit,
          selected: selectedHash === commit.hash,
          isLarge: commit.additions + commit.deletions >= largeThreshold && largeThreshold > 0,
          onSelect: () => onSelectHash(commit.hash),
        },
        width: NODE_W,
        height: NODE_H,
      })),
    [chronologic, selectedHash, largeThreshold, onSelectHash],
  );

  const edges: Edge[] = useMemo(
    () =>
      chronologic.slice(0, -1).map((commit, index) => ({
        id: `${commit.hash}-${chronologic[index + 1].hash}`,
        source: commit.hash,
        target: chronologic[index + 1].hash,
        style: { stroke: "#30363d", strokeWidth: 1 },
      })),
    [chronologic],
  );

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(() => {
      void fitView({ padding: 0.22, duration: reduce ? 0 : 180 });
    }, 40);
    return () => window.clearTimeout(timer);
  }, [commits.length, fitView]);

  if (commits.length === 0) {
    return <p className="empty">No commits available to visualize.</p>;
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.22 }}
      minZoom={0.35}
      maxZoom={1.6}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable
      panOnScroll
      zoomOnScroll
      onNodeClick={(_event, node) => onSelectHash(node.id)}
      proOptions={{ hideAttribution: false }}
    >
      <Background color="#30363d" gap={18} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
