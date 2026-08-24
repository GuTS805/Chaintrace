"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  Position,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphNode, GraphResult } from "@/lib/types";
import { assetAmount, formatAsset, shortAddr } from "@/lib/format";
import { Eyebrow, Pill, Tile } from "./ui";

type Role = "root" | "risk" | "bridge" | "vasp" | "plain";

const ROLE_COLOR: Record<Role, string> = {
  root: "#6366f1",
  risk: "#ef4444",
  bridge: "#22d3ee",
  vasp: "#22c55e",
  plain: "#5b6472",
};

function roleOf(n: GraphNode): Role {
  if (n.depth === 0) return "root";
  if (n.label_name && /tornado|mixer|sanction|ofac/i.test(n.label_name)) return "risk";
  if (n.label_name && /bridge|wormhole|stargate|multichain|across protocol/i.test(n.label_name))
    return "bridge";
  if (n.vasp_name) return "vasp";
  return "plain";
}

// Distinct deposit clusters (same cluster_id -> swept into the same hot
// wallet) get a shared subtle background tint so they read as a group.
const CLUSTER_TINTS = ["#121319", "#141219", "#0f1613", "#171213", "#0f1517", "#131017"];

function clusterTint(clusterId: number | null | undefined): string {
  if (clusterId == null) return "#0e0e0e";
  return CLUSTER_TINTS[clusterId % CLUSTER_TINTS.length];
}

function nodeStyle(role: Role, clusterId: number | null | undefined, isHighlighted: boolean): React.CSSProperties {
  const color = ROLE_COLOR[role];
  const special = role !== "plain";
  return {
    background: clusterTint(clusterId),
    border: `${special || isHighlighted ? 1.5 : 1}px solid ${isHighlighted ? "#6366f1" : color}`,
    borderRadius: 6,
    color: "#f5f5f5",
    fontSize: 11,
    fontFamily: "var(--font-geist-mono), ui-monospace, monospace",
    padding: "6px 10px",
    width: 178,
    boxShadow: isHighlighted ? "0 0 0 3px rgba(99,102,241,0.2)" : "none",
    transition: "box-shadow 150ms ease, border-color 150ms ease",
  };
}

export function GraphView({
  graph,
  highlightedTx,
  highlightedNode,
  riskAddresses,
  onNodeFocus,
}: {
  graph: GraphResult;
  highlightedTx: Set<string>;
  highlightedNode: string | null;
  riskAddresses: Set<string>;
  onNodeFocus: (address: string, isRoot: boolean) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const byDepth = new Map<number, GraphNode[]>();
    for (const n of graph.nodes) {
      const arr = byDepth.get(n.depth) ?? [];
      arr.push(n);
      byDepth.set(n.depth, arr);
    }
    const nodeIds = new Set(graph.nodes.map((n) => n.address));
    const roleByAddr = new Map(graph.nodes.map((n) => [n.address, roleOf(n)]));

    const rfNodes: Node[] = graph.nodes.map((n) => {
      const peers = byDepth.get(n.depth) ?? [];
      const idx = peers.indexOf(n);
      const role = roleOf(n);
      const title = n.vasp_name ?? n.label_name ?? "";
      const flagged = riskAddresses.has(n.address);
      const isHl = highlightedNode === n.address;
      return {
        id: n.address,
        position: { x: 40 + n.depth * 250, y: 30 + idx * 84 },
        data: {
          label: (
            <div className="relative">
              {flagged && (
                <span
                  className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-bad"
                  title="Risk indicator on this address"
                />
              )}
              <div>{shortAddr(n.address)}</div>
              {title && (
                <div style={{ color: ROLE_COLOR[role], marginTop: 2, fontWeight: 600 }}>{title}</div>
              )}
              {n.cluster_id != null && (
                <div style={{ color: "#71717a", marginTop: 2, fontSize: 9 }}>
                  cluster #{n.cluster_id}
                </div>
              )}
            </div>
          ),
        },
        className: isHl ? "animate-pulse-ring rounded-lg" : undefined,
        style: nodeStyle(role, n.cluster_id, isHl),
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });

    const seen = new Set<string>();
    const rfEdges: Edge[] = [];
    for (const e of graph.edges) {
      if (!nodeIds.has(e.from_address) || !nodeIds.has(e.to_address)) continue;
      if (seen.has(e.tx_hash)) continue;
      seen.add(e.tx_hash);
      const amt = assetAmount(e.value_wei, e.asset);
      const width = Math.max(1, Math.min(4, 1 + Math.log10(1 + amt)));
      const toVasp = roleByAddr.get(e.to_address) === "vasp";
      const isHl = highlightedTx.has(e.tx_hash);
      const stroke = isHl ? "#6366f1" : toVasp ? "#22c55e" : "#3a4150";
      rfEdges.push({
        id: e.tx_hash,
        source: e.from_address,
        target: e.to_address,
        label: formatAsset(e.value_wei, e.asset),
        labelStyle: { fill: isHl ? "#a5b4fc" : "#a1a1aa", fontSize: 9, fontWeight: isHl ? 600 : 400 },
        labelBgStyle: { fill: "#050505", fillOpacity: 0.85 },
        style: { stroke, strokeWidth: isHl ? width + 1.5 : width },
        className: isHl ? "trace-edge" : undefined,
        markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 16, height: 16 },
        animated: toVasp && !isHl,
        zIndex: isHl ? 10 : 0,
      });
    }
    return { nodes: rfNodes, edges: rfEdges };
  }, [graph, highlightedTx, highlightedNode, riskAddresses]);

  return (
    <Tile bodyClassName="p-6">
      <div className="flex items-center justify-between pb-5">
        <Eyebrow>Transaction graph</Eyebrow>
        {graph.prune.pruned ? (
          <Pill tone="warn">pruned: {graph.prune.reasons.join(", ")}</Pill>
        ) : (
          <Pill tone="muted">{graph.prune.nodes_visited} nodes</Pill>
        )}
      </div>
      <div className="h-[640px] w-full overflow-hidden rounded-md">
        {graph.nodes.length === 0 ? (
          <p className="p-6 text-sm text-muted">No outgoing activity within bounds.</p>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodeClick={(_, node) => onNodeFocus(node.id, node.id === graph.root)}
            nodesDraggable={false}
            nodesConnectable={false}
            fitView
            minZoom={0.2}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#161616" gap={28} />
            <Controls showInteractive={false} className="!border-border !bg-panel [&_button]:!border-border [&_button]:!bg-panel [&_button]:!fill-muted [&_button]:hover:!bg-panel2" />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => {
                const gn = graph.nodes.find((x) => x.address === n.id);
                return gn ? ROLE_COLOR[roleOf(gn)] : "#5b6472";
              }}
              maskColor="rgba(5,5,5,0.75)"
              style={{ background: "#0a0a0a", border: "1px solid rgba(255,255,255,0.08)" }}
            />
          </ReactFlow>
        )}
      </div>
      <p className="pt-4 text-[11px] text-dim">
        Click a node to inspect inline · root <span className="text-accent">indigo</span> · attributed{" "}
        <span className="text-good">green</span> · mixer <span className="text-bad">red</span> · bridge{" "}
        <span style={{ color: "#22d3ee" }}>cyan</span> · hovering evidence traces the matching edge here
      </p>
    </Tile>
  );
}
