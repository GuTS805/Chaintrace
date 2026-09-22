"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  AlertTriangle,
  Building2,
  Crosshair,
  Waypoints,
  Wallet as WalletIcon,
} from "lucide-react";
import type { GraphNode, GraphResult } from "@/lib/types";
import { assetAmount, formatAsset, shortAddr } from "@/lib/format";
import { Eyebrow, Pill, Tile } from "./ui";

type Role = "root" | "risk" | "bridge" | "vasp" | "plain";

const ROLE_COLOR: Record<Role, string> = {
  root: "#67E8F9",
  risk: "#F16B5C",
  bridge: "#38BDF8",
  vasp: "#3ED18E",
  plain: "#847F73",
};

const ROLE_ICON: Record<Role, typeof WalletIcon> = {
  root: Crosshair,
  risk: AlertTriangle,
  bridge: Waypoints,
  vasp: Building2,
  plain: WalletIcon,
};

const ROLE_LABEL: Record<Role, string> = {
  root: "Subject wallet",
  risk: "Risk exposure",
  bridge: "Bridge / mixer",
  vasp: "Exchange (VASP)",
  plain: "Wallet",
};

function roleOf(n: GraphNode): Role {
  if (n.depth === 0) return "root";
  if (n.label_name && /tornado|mixer|sanction|ofac/i.test(n.label_name)) return "risk";
  if (n.label_name && /bridge|wormhole|stargate|multichain|across protocol/i.test(n.label_name))
    return "bridge";
  if (n.vasp_name) return "vasp";
  return "plain";
}

// Low-key dark tints for cluster grouping — same hue family as the node's
// role color, just enough to read as "grouped" against the near-black canvas.
const CLUSTER_TINTS = ["#1C1930", "#242040", "#122619", "#2A1414", "#0F1E26", "#1E1A28"];

function clusterTint(clusterId: number | null | undefined): string {
  if (clusterId == null) return "#181b34";
  return CLUSTER_TINTS[clusterId % CLUSTER_TINTS.length];
}

interface WalletNodeData {
  address: string;
  role: Role;
  title: string;
  clusterId: number | null | undefined;
  flagged: boolean;
  isHighlighted: boolean;
  isRoot: boolean;
}

/** A wallet/exchange card, not a generic React Flow box — an icon badge for
 * what the address *is*, its role spelled out, and a persistent role-tinted
 * glow so the graph reads at a glance before you look at any single node. */
function WalletNode({ data }: NodeProps<WalletNodeData>) {
  const color = ROLE_COLOR[data.role];
  const Icon = ROLE_ICON[data.role];
  const special = data.role !== "plain";

  return (
    <div
      className="relative flex items-center gap-2.5 rounded-2xl px-3.5 py-3 transition-shadow duration-150"
      style={{
        background: clusterTint(data.clusterId),
        border: `${special || data.isHighlighted ? 2 : 1}px solid ${data.isHighlighted ? "#67E8F9" : color}`,
        width: 208,
        boxShadow: data.isHighlighted
          ? "0 0 0 5px rgba(103,232,249,0.16), 0 8px 24px -8px rgba(103,232,249,0.35)"
          : `0 8px 20px -10px rgba(0,0,0,0.7), 0 0 0 1px rgba(0,0,0,0.2), 0 0 22px -6px ${color}33`,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0, left: -2 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0, right: -2 }} />

      {data.flagged && (
        <span
          className="absolute -right-1.5 -top-1.5 h-3 w-3 rounded-full border-2 border-[#0A0A0A] bg-bad-text"
          title="Risk indicator on this address"
        />
      )}

      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
        style={{ background: `${color}22`, color }}
      >
        <Icon size={15} />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className="cursor-pointer font-mono text-[11px] font-medium text-heading hover:underline"
          title={`${data.address} — click to copy`}
          onClick={(e) => {
            e.stopPropagation();
            navigator.clipboard?.writeText(data.address).catch(() => {});
          }}
        >
          {shortAddr(data.address)}
        </div>
        <div className="mt-0.5 truncate text-[10px] font-semibold" style={{ color }}>
          {data.title || ROLE_LABEL[data.role]}
        </div>
        {data.clusterId != null && (
          <div className="mt-0.5 text-[9px] text-muted">cluster #{data.clusterId}</div>
        )}
      </div>
    </div>
  );
}

const nodeTypes = { wallet: WalletNode };

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

    const rfNodes: Node<WalletNodeData>[] = graph.nodes.map((n) => {
      const peers = byDepth.get(n.depth) ?? [];
      const idx = peers.indexOf(n);
      const role = roleOf(n);
      const isHl = highlightedNode === n.address;
      return {
        id: n.address,
        type: "wallet",
        position: { x: 40 + n.depth * 280, y: 30 + idx * 100 },
        data: {
          address: n.address,
          role,
          title: n.vasp_name ?? n.label_name ?? "",
          clusterId: n.cluster_id,
          flagged: riskAddresses.has(n.address),
          isHighlighted: isHl,
          isRoot: n.depth === 0,
        },
        className: isHl ? "animate-pulse-ring rounded-2xl" : undefined,
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
      const stroke = isHl ? "#67E8F9" : toVasp ? "#3ED18E" : "#56657c";
      rfEdges.push({
        id: e.tx_hash,
        source: e.from_address,
        target: e.to_address,
        type: "smoothstep",
        pathOptions: { borderRadius: 16 },
        label: formatAsset(e.value_wei, e.asset),
        labelStyle: {
          fill: isHl ? "#67E8F9" : "#C3C5DE",
          fontSize: 10,
          fontWeight: isHl ? 700 : 500,
        },
        labelBgStyle: { fill: "#14162d", fillOpacity: 1 },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 5,
        style: { stroke, strokeWidth: isHl ? width + 1.5 : width },
        className: isHl ? "trace-edge" : undefined,
        markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 18, height: 18 },
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
      <div className="h-[420px] sm:h-[560px] lg:h-[640px] w-full overflow-hidden rounded-card">
        {graph.nodes.length === 0 ? (
          <p className="p-6 text-sm text-muted">No outgoing activity within bounds.</p>
        ) : (
          <ReactFlow
            aria-label="Wallet transaction graph"
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => onNodeFocus(node.id, node.id === graph.root)}
            nodesDraggable={false}
            nodesConnectable={false}
            fitView
            minZoom={0.2}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#263246" gap={28} />
            <Controls
              showInteractive={false}
              className="!rounded-btn !border-soft-border !bg-surface !shadow-card [&_button]:!border-soft-border [&_button]:!bg-surface [&_button]:!fill-muted [&_button]:hover:!bg-surface-lavender"
            />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => {
                const gn = graph.nodes.find((x) => x.address === n.id);
                return gn ? ROLE_COLOR[roleOf(gn)] : "#847F73";
              }}
              maskColor="rgba(10,10,10,0.75)"
              style={{ background: "#14162d", border: "1px solid rgba(243,241,234,0.1)", borderRadius: 12 }}
            />
          </ReactFlow>
        )}
      </div>
      <p className="pt-4 text-[11px] text-muted">
        Click a node to inspect inline · root <span className="text-primary">cyan</span> · attributed{" "}
        <span className="text-good-text">green</span> · mixer <span className="text-bad-text">red</span> · bridge{" "}
        <span style={{ color: "#38BDF8" }}>blue</span> · hovering evidence traces the matching edge here
      </p>
    </Tile>
  );
}
