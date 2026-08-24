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
import { Panel, Pill } from "./ui";

type Role = "root" | "risk" | "bridge" | "vasp" | "plain";

const ROLE_COLOR: Record<Role, string> = {
  root: "#8b7cff",
  risk: "#ff5c72",
  bridge: "#3dd6e8",
  vasp: "#e8a33d",
  plain: "#565a72",
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
const CLUSTER_TINTS = ["#1b2038", "#241d33", "#132a26", "#2b1f24", "#132630", "#231a30"];

function clusterTint(clusterId: number | null | undefined): string {
  if (clusterId == null) return "#181a26";
  return CLUSTER_TINTS[clusterId % CLUSTER_TINTS.length];
}

function nodeStyle(role: Role, clusterId: number | null | undefined, isHighlighted: boolean): React.CSSProperties {
  const color = ROLE_COLOR[role];
  const special = role !== "plain";
  return {
    background: clusterTint(clusterId),
    border: `${special || isHighlighted ? 1.5 : 1}px solid ${isHighlighted ? "#8b7cff" : color}`,
    borderRadius: 8,
    color: "#e7e7f0",
    fontSize: 11,
    fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
    padding: "6px 10px",
    width: 178,
    boxShadow: isHighlighted
      ? "0 0 0 3px rgba(139,124,255,0.25), 0 0 20px rgba(139,124,255,0.35)"
      : "0 1px 3px rgba(0,0,0,0.4)",
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
                <div style={{ color: "#8688a3", marginTop: 2, fontSize: 9 }}>
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
      const stroke = isHl ? "#8b7cff" : toVasp ? "#e8a33d" : "#4a4e68";
      rfEdges.push({
        id: e.tx_hash,
        source: e.from_address,
        target: e.to_address,
        label: formatAsset(e.value_wei, e.asset),
        labelStyle: { fill: isHl ? "#c7bfff" : "#8688a3", fontSize: 9, fontWeight: isHl ? 600 : 400 },
        labelBgStyle: { fill: "#0a0b10", fillOpacity: 0.85 },
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
    <Panel
      title="Transaction graph"
      className="overflow-hidden"
      bodyClassName="p-0"
      right={
        graph.prune.pruned ? (
          <Pill tone="warn">pruned: {graph.prune.reasons.join(", ")}</Pill>
        ) : (
          <Pill tone="muted">{graph.prune.nodes_visited} nodes</Pill>
        )
      }
    >
      <div className="h-[560px] w-full">
        {graph.nodes.length === 0 ? (
          <p className="p-4 text-sm text-muted">No outgoing activity within bounds.</p>
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
            <Background color="#1a1c28" gap={24} />
            <Controls showInteractive={false} className="!border-border !bg-panel [&_button]:!border-border [&_button]:!bg-panel [&_button]:!fill-muted [&_button]:hover:!bg-panel2" />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => {
                const gn = graph.nodes.find((x) => x.address === n.id);
                return gn ? ROLE_COLOR[roleOf(gn)] : "#565a72";
              }}
              maskColor="rgba(10,11,16,0.75)"
              style={{ background: "#14161f", border: "1px solid #272a3b" }}
            />
          </ReactFlow>
        )}
      </div>
      <p className="border-t border-border px-4 py-2 text-[10px] uppercase tracking-widest text-muted">
        click a node to inspect inline · root <span className="text-accent">violet</span> · attributed{" "}
        <span className="text-gold">gold</span> · mixer <span className="text-bad">rose</span> · bridge{" "}
        <span style={{ color: "#3dd6e8" }}>cyan</span> · hovering evidence traces the matching edge here
      </p>
    </Panel>
  );
}
