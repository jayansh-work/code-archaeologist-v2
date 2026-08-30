"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import CommitNode, { type CommitFlowNode } from "@/components/CommitNode";
import { computeButterfly } from "@/lib/butterfly";
import { NODE_H, NODE_W, columnCount, snakePosition } from "@/lib/graphLayout";
import type { CommitEvidence } from "@/lib/types";

const nodeTypes = { commit: CommitNode } as NodeTypes;

const TIMELINE_STROKE = "#30363d";
const RIPPLE_STROKE = "#2f81f7";

type EvolutionGraphProps = {
  commits: CommitEvidence[];
  selectedHash: string | null;
  onSelectHash: (hash: string) => void;
};

export default function EvolutionGraph(props: EvolutionGraphProps) {
  const [columns, setColumns] = useState(4);
  const shellRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) {
      return;
    }
    const apply = () => setColumns(columnCount(shell.clientWidth));
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(shell);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="graph-shell" ref={shellRef}>
      <ReactFlowProvider key={props.commits[0]?.hash ?? "empty"}>
        <GraphCanvas {...props} columns={columns} />
      </ReactFlowProvider>
    </div>
  );
}

function handlesFor(sourceIndex: number, targetIndex: number, columns: number) {
  const sourceRow = Math.floor(sourceIndex / columns);
  const targetRow = Math.floor(targetIndex / columns);
  if (sourceRow === targetRow) {
    return { sourceHandle: "right", targetHandle: "left" };
  }
  return { sourceHandle: "bottom", targetHandle: "top" };
}

function GraphCanvas({
  commits,
  selectedHash,
  onSelectHash,
  columns,
}: EvolutionGraphProps & { columns: number }) {
  const { fitView } = useReactFlow();
  const chronologic = useMemo(() => [...commits].reverse(), [commits]);
  const indexByHash = useMemo(
    () => new Map(chronologic.map((commit, index) => [commit.hash, index])),
    [chronologic],
  );
  const churns = useMemo(
    () => chronologic.map((commit) => commit.additions + commit.deletions).sort((a, b) => a - b),
    [chronologic],
  );
  const largeThreshold = churns[Math.floor(churns.length * 0.8)] ?? 0;
  const origin = chronologic.find((commit) => commit.hash === selectedHash) ?? null;
  const butterfly = useMemo(
    () => (origin ? computeButterfly(commits, origin) : null),
    [commits, origin],
  );
  const related = useMemo(() => {
    if (!butterfly) {
      return new Set<string>();
    }
    return new Set([
      butterfly.origin.hash,
      ...butterfly.upstream.map((item) => item.commit.hash),
      ...butterfly.downstream.map((item) => item.commit.hash),
    ]);
  }, [butterfly]);

  const nodes: CommitFlowNode[] = useMemo(
    () =>
      chronologic.map((commit, index) => ({
        id: commit.hash,
        type: "commit",
        position: snakePosition(index, columns),
        selected: selectedHash === commit.hash,
        data: {
          commit,
          selected: selectedHash === commit.hash,
          isLarge: commit.additions + commit.deletions >= largeThreshold && largeThreshold > 0,
          dimmed: Boolean(selectedHash) && !related.has(commit.hash),
          ripple: Boolean(selectedHash) && related.has(commit.hash) && commit.hash !== selectedHash,
          onSelect: () => onSelectHash(commit.hash),
        },
        width: NODE_W,
        height: NODE_H,
      })),
    [chronologic, selectedHash, largeThreshold, onSelectHash, columns, related],
  );

  const edges: Edge[] = useMemo(() => {
    const consecutive = new Set(
      chronologic.slice(0, -1).map((commit, index) => `${commit.hash}->${chronologic[index + 1].hash}`),
    );
    const timeline: Edge[] = chronologic.slice(0, -1).map((commit, index) => {
      const target = chronologic[index + 1];
      const handles = handlesFor(index, index + 1, columns);
      return {
        id: `${commit.hash}-${target.hash}`,
        source: commit.hash,
        target: target.hash,
        sourceHandle: handles.sourceHandle,
        targetHandle: handles.targetHandle,
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: TIMELINE_STROKE },
        style: { stroke: TIMELINE_STROKE, strokeWidth: 1.5 },
      };
    });
    if (!butterfly || !origin) {
      return timeline;
    }
    const ripplePairs: { source: string; target: string }[] = [
      ...butterfly.upstream.slice(0, 3).map((item) => ({ source: item.commit.hash, target: origin.hash })),
      ...butterfly.downstream.slice(0, 3).map((item) => ({ source: origin.hash, target: item.commit.hash })),
    ];
    const ripple: Edge[] = [];
    for (const pair of ripplePairs) {
      const key = `${pair.source}->${pair.target}`;
      if (consecutive.has(key)) {
        continue;
      }
      const sourceIndex = indexByHash.get(pair.source);
      const targetIndex = indexByHash.get(pair.target);
      if (sourceIndex === undefined || targetIndex === undefined) {
        continue;
      }
      const handles = handlesFor(sourceIndex, targetIndex, columns);
      ripple.push({
        id: `bf-${pair.source}-${pair.target}`,
        source: pair.source,
        target: pair.target,
        sourceHandle: handles.sourceHandle,
        targetHandle: handles.targetHandle,
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: RIPPLE_STROKE },
        style: { stroke: RIPPLE_STROKE, strokeWidth: 1.5, strokeDasharray: "5 4" },
        zIndex: 4,
      });
    }
    return [...timeline, ...ripple];
  }, [chronologic, columns, butterfly, origin, indexByHash]);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(() => {
      void fitView({ padding: 0.18, duration: reduce ? 0 : 160 });
    }, 40);
    return () => window.clearTimeout(timer);
  }, [commits.length, columns, fitView]);

  if (commits.length === 0) {
    return <p className="empty">No commits available to visualize.</p>;
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.18 }}
      minZoom={0.2}
      maxZoom={1.5}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable
      panOnScroll={false}
      zoomOnScroll={false}
      zoomOnPinch
      zoomOnDoubleClick={false}
      panOnDrag
      colorMode="dark"
      onNodeClick={(_event, node) => onSelectHash(node.id)}
      proOptions={{ hideAttribution: false }}
    >
      <Background color="#30363d" gap={18} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
