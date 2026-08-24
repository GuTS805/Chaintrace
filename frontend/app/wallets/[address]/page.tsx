"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AttributionResult, GraphResult, RiskResult } from "@/lib/types";
import { pushRecent } from "@/lib/recents";
import { AttributionPanel } from "@/components/AttributionPanel";
import { RiskPanel } from "@/components/RiskPanel";
import { GraphView } from "@/components/GraphView";
import { NodeFocusDrawer } from "@/components/NodeFocusDrawer";
import { AddToCase } from "@/components/AddToCase";
import { WalletSearch } from "@/components/WalletSearch";
import { LiveTrace } from "@/components/LiveTrace";
import { PdfButton } from "@/components/PdfButton";
import { Panel } from "@/components/ui";

export default function WalletPage({
  params,
}: {
  params: { address: string };
}) {
  const decoded = decodeURIComponent(params.address);
  // EVM addresses are case-insensitive hex; Tron (and other base58) addresses
  // are case-sensitive/checksummed and must not be lowercased.
  const address = decoded.toLowerCase().startsWith("0x") ? decoded.toLowerCase() : decoded;
  const chain = address.startsWith("T") ? "TRON" : "ETHEREUM";
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Cross-highlight state, shared by AttributionPanel/RiskPanel (source) and
  // GraphView (destination) — hovering evidence or a risk indicator traces
  // the matching edge/node in the graph in place, instead of three panels
  // that don't reference each other.
  const [highlightedTx, setHighlightedTx] = useState<Set<string>>(new Set());
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const [focusedNode, setFocusedNode] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      api.attribution(address),
      api.risk(address),
      api.graph(address, 5),
    ]);
    const [a, r, g] = results;
    if (a.status === "fulfilled") setAttribution(a.value);
    if (r.status === "fulfilled") setRisk(r.value);
    if (g.status === "fulfilled") setGraph(g.value);
    if (results.every((x) => x.status === "rejected")) {
      const first = results.find((x) => x.status === "rejected") as
        | PromiseRejectedResult
        | undefined;
      setError(
        first ? String(first.reason) : "Could not reach the API. Is it running?",
      );
    }
    setLoading(false);
  }, [address]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!loading && !error) pushRecent(address);
  }, [address, loading, error]);

  // A wallet with no local data: no candidates and an empty graph.
  const isEmpty =
    (attribution?.candidates.length ?? 0) === 0 &&
    (graph?.nodes.length ?? 0) <= 1;

  const riskAddresses = new Set(risk?.indicators.map((i) => i.address) ?? []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-base font-semibold">
          <span className="text-muted">wallet</span>{" "}
          <span className="break-all font-mono text-accent">{address}</span>{" "}
          <span className="rounded border border-border px-1.5 py-0.5 text-[10px] uppercase tracking-widest text-muted">
            {chain}
          </span>
        </h1>
        <PdfButton
          path={`/wallets/${address}/report`}
          className="rounded border border-border px-3 py-2 text-xs text-muted hover:border-accent hover:text-accent"
        >
          ↓ report (PDF)
        </PdfButton>
        {attribution &&
          !attribution.insufficient_evidence &&
          attribution.candidates.length > 0 && (
            <PdfButton
              path={`/wallets/${address}/disclosure-request`}
              className="rounded border border-gold/50 bg-gold/10 px-3 py-2 text-xs text-gold hover:bg-gold/20"
            >
              ⚖ disclosure request (SAHYOG)
            </PdfButton>
          )}
        <div className="ml-auto w-full max-w-md">
          <WalletSearch />
        </div>
      </div>

      {loading && <p className="text-sm text-muted">Tracing…</p>}
      {error && (
        <Panel title="Error">
          <p className="text-sm text-bad">{error}</p>
          <p className="mt-2 text-xs text-muted">
            Start the backend (<code className="text-text">make dev</code>) and
            seed data (<code className="text-text">make seed-demo</code>).
          </p>
        </Panel>
      )}

      {!loading && !error && isEmpty && (
        <LiveTrace address={address} onDone={load} />
      )}

      {!loading && !error && !isEmpty && (
        <>
          {/* Graph as the spine: evidence rail references it in place via
              hover; risk + case sit below rather than competing for the
              primary reading position. */}
          <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-5">
            <div className="xl:col-span-2">
              {attribution && (
                <AttributionPanel
                  result={attribution}
                  onHoverEvidence={(hashes) => setHighlightedTx(new Set(hashes ?? []))}
                />
              )}
            </div>
            <div className="xl:col-span-3">
              {graph && (
                <GraphView
                  graph={graph}
                  highlightedTx={highlightedTx}
                  highlightedNode={highlightedNode}
                  riskAddresses={riskAddresses}
                  onNodeFocus={(addr, isRoot) => {
                    if (!isRoot) setFocusedNode(addr);
                  }}
                />
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {risk && (
              <RiskPanel
                risk={risk}
                onHoverIndicator={(addr) => setHighlightedNode(addr)}
              />
            )}
            <AddToCase address={address} attribution={attribution} />
          </div>
        </>
      )}

      {focusedNode && (
        <NodeFocusDrawer address={focusedNode} onClose={() => setFocusedNode(null)} />
      )}
    </div>
  );
}
