"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import ReactFlow, {
  Background,
  Controls,
  Position,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphResult } from "@/lib/types";
import { shortAddr, weiToEth } from "@/lib/format";
import { Panel, Pill } from "./ui";

function nodeStyle(
  isRoot: boolean,
  category: string | null,
  isVasp: boolean,
): React.CSSProperties {
  let border = "#2a3646";
  let color = "#c9d1d9";
  if (isRoot) {
    border = "#39bae6";
    color = "#39bae6";
  } else if (category === "SANCTIONED" || category === "MIXER") {
    border = "#f07178";
    color = "#f07178";
  } else if (isVasp) {
    border = "#b18cff";
    color = "#b18cff";
  }
  return {
    background: "#0f1620",
    border: `1px solid ${border}`,
    borderRadius: 6,
    color,
    fontSize: 11,
    fontFamily: "var(--font-mono), monospace",
    padding: "6px 10px",
    width: 170,
  };
}

export function GraphView({ graph }: { graph: GraphResult }) {
  const router = useRouter();

  const { nodes, edges } = useMemo(() => {
    const byDepth = new Map<number, typeof graph.nodes>();
    for (const n of graph.nodes) {
      const arr = byDepth.get(n.depth) ?? [];
      arr.push(n);
      byDepth.set(n.depth, arr);
    }
    const nodeIds = new Set(graph.nodes.map((n) => n.address));

    const rfNodes: Node[] = graph.nodes.map((n) => {
      const peers = byDepth.get(n.depth) ?? [];
      const idx = peers.indexOf(n);
      const isRoot = n.depth === 0;
      // Category is only known for labeled nodes; infer risky ones by name.
      const category =
        n.label_name && /tornado|mixer/i.test(n.label_name)
          ? "MIXER"
          : n.label_name && /sanction|ofac/i.test(n.label_name)
            ? "SANCTIONED"
            : null;
      const title = n.vasp_name ?? n.label_name ?? "";
      return {
        id: n.address,
        position: { x: 40 + n.depth * 240, y: 30 + idx * 74 },
        data: {
          label: (
            <div>
              <div>{shortAddr(n.address)}</div>
              {title && (
                <div style={{ opacity: 0.8, marginTop: 2 }}>{title}</div>
              )}
            </div>
          ),
        },
        style: nodeStyle(isRoot, category, Boolean(n.vasp_name)),
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });

    const seen = new Set<string>();
    const rfEdges: Edge[] = [];
    for (const e of graph.edges) {
      if (!nodeIds.has(e.from_address) || !nodeIds.has(e.to_address)) continue;
      const id = e.tx_hash;
      if (seen.has(id)) continue;
      seen.add(id);
      rfEdges.push({
        id,
        source: e.from_address,
        target: e.to_address,
        label: `${weiToEth(e.value_wei, 2)} ETH`,
        labelStyle: { fill: "#6b7684", fontSize: 9 },
        labelBgStyle: { fill: "#0a0e14" },
        style: { stroke: "#2a3646" },
        animated: false,
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
            <Background color="#1c2530" gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
      </div>
      <p className="mt-2 text-[10px] text-muted">
        Click any node to trace that wallet. Root = cyan · VASP = purple ·
        sanctioned/mixer = red.
      </p>
    </Panel>
  );
}
