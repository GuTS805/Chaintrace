"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
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
import { shortAddr, weiToEth } from "@/lib/format";
import { Panel, Pill } from "./ui";

type Role = "root" | "risk" | "vasp" | "plain";

const ROLE_COLOR: Record<Role, string> = {
  root: "#4f46e5",
  risk: "#d11f2f",
  vasp: "#6d28d9",
  plain: "#cbd3dd",
};

function roleOf(n: GraphNode): Role {
  if (n.depth === 0) return "root";
  if (n.label_name && /tornado|mixer|sanction|ofac/i.test(n.label_name)) return "risk";
  if (n.vasp_name) return "vasp";
  return "plain";
}

function nodeStyle(role: Role): React.CSSProperties {
  const color = ROLE_COLOR[role];
  const special = role !== "plain";
  return {
    background: "#ffffff",
    border: `${special ? 1.5 : 1}px solid ${color}`,
    borderRadius: 8,
    color: "#0f1720",
    fontSize: 11,
    fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
    padding: "6px 10px",
    width: 176,
    boxShadow: "0 1px 2px rgba(16,23,32,0.08)",
  };
}

export function GraphView({ graph }: { graph: GraphResult }) {
  const router = useRouter();

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
      return {
        id: n.address,
        position: { x: 40 + n.depth * 250, y: 30 + idx * 78 },
        data: {
          label: (
            <div>
              <div>{shortAddr(n.address)}</div>
              {title && (
                <div style={{ color: ROLE_COLOR[role], marginTop: 2, fontWeight: 600 }}>
                  {title}
                </div>
              )}
            </div>
          ),
        },
        style: nodeStyle(role),
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
      const eth = Number(e.value_wei) / 1e18;
      const width = Math.max(1, Math.min(4, 1 + Math.log10(1 + eth)));
      const toVasp = roleByAddr.get(e.to_address) === "vasp";
      const stroke = toVasp ? "#4f46e5" : "#9aa4b2";
      rfEdges.push({
        id: e.tx_hash,
        source: e.from_address,
        target: e.to_address,
        label: `${weiToEth(e.value_wei, 2)} ETH`,
        labelStyle: { fill: "#5b6673", fontSize: 9 },
        labelBgStyle: { fill: "#ffffff", fillOpacity: 0.85 },
        style: { stroke, strokeWidth: width },
        markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 16, height: 16 },
        animated: toVasp,
      });
    }
    return { nodes: rfNodes, edges: rfEdges };
  }, [graph]);

  return (
    <Panel
      title="Transaction graph"
      right={
        graph.prune.pruned ? (
          <Pill tone="warn">pruned: {graph.prune.reasons.join(", ")}</Pill>
        ) : (
          <Pill tone="muted">{graph.prune.nodes_visited} nodes</Pill>
        )
      }
      className="overflow-hidden"
    >
      <div className="h-[520px] w-full">
        {graph.nodes.length === 0 ? (
          <p className="text-sm text-muted">No outgoing activity within bounds.</p>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodeClick={(_, node) => router.push(`/wallets/${node.id}`)}
            fitView
            minZoom={0.2}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#e2e7ee" gap={22} />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => {
                const addr = n.id;
                const gn = graph.nodes.find((x) => x.address === addr);
                return gn ? ROLE_COLOR[roleOf(gn)] : "#cbd3dd";
              }}
              maskColor="rgba(15,23,32,0.06)"
              style={{ background: "#f6f7f9", border: "1px solid #d8dee7" }}
            />
          </ReactFlow>
        )}
      </div>
      <p className="mt-2 text-[10px] uppercase tracking-widest text-muted">
        click a node to trace · root <span className="text-accent">indigo</span> ·
        VASP <span className="text-vasp">violet</span> · mixer{" "}
        <span className="text-bad">red</span> · arrow = fund flow, thicker = larger
      </p>
    </Panel>
  );
}
