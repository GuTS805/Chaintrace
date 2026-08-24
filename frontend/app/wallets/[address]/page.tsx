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
import { BentoGrid, Eyebrow, Tile } from "@/components/ui";

export default function WalletPage({
  params,
}: {
  params: { address: string };
}) {
  const decoded = decodeURIComponent(params.address);
  // EVM addresses are case-insensitive hex; Tron (and other base58) addresses
  // are case-sensitive/checksummed and must not be lowercased.
  const address = decoded.toLowerCase().startsWith("0x") ? decoded.toLowerCase() : decoded;
  // A live trace tells us the real chain queried; until then, EVM addresses
  // default to "ethereum" in the badge.
  const [resolvedChain, setResolvedChain] = useState<string | null>(null);
  const chain = (resolvedChain ?? (address.startsWith("T") ? "tron" : "ethereum")).toUpperCase();
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Cross-highlight state, shared by AttributionPanel/RiskPanel (source) and
  // GraphView (destination).
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
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <Eyebrow>Trace wallet · {chain}</Eyebrow>
          <h1 className="mt-2 break-all font-mono text-[15px] text-mono">{address}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PdfButton
            path={`/wallets/${address}/report`}
            className="rounded-btn border border-soft-border px-3 py-2 text-[12px] text-muted transition-all hover:bg-surface-lavender hover:text-heading"
          >
            Report (PDF)
          </PdfButton>
          {attribution &&
            !attribution.insufficient_evidence &&
            attribution.candidates.length > 0 && (
              <PdfButton
                path={`/wallets/${address}/disclosure-request`}
                className="rounded-btn bg-primary px-3 py-2 text-[12px] font-medium text-white shadow-button transition-all hover:-translate-y-0.5 hover:bg-primary-hover active:translate-y-0"
              >
                Prepare disclosure request (SAHYOG)
              </PdfButton>
            )}
        </div>
      </div>

      <div className="max-w-md">
        <WalletSearch />
      </div>

      {loading && <p className="text-sm text-muted">Tracing…</p>}
      {error && (
        <Tile title="Error">
          <p className="text-sm text-bad-text">{error}</p>
          <p className="mt-2 text-xs text-muted">
            Start the backend (<code className="rounded-lg bg-surface-lavender px-1.5 py-0.5 font-mono text-mono">make dev</code>) and
            seed data (<code className="rounded-lg bg-surface-lavender px-1.5 py-0.5 font-mono text-mono">make seed-demo</code>).
          </p>
        </Tile>
      )}

      {!loading && !error && isEmpty && (
        <LiveTrace
          address={address}
          onDone={(usedChain) => {
            setResolvedChain(usedChain);
            void load();
          }}
        />
      )}

      {!loading && !error && !isEmpty && (
        <div className="space-y-10">
          {attribution && (
            <AttributionPanel
              result={attribution}
              onHoverEvidence={(hashes) => setHighlightedTx(new Set(hashes ?? []))}
            />
          )}

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

          <BentoGrid>
            <div className="col-span-4 md:col-span-7">
              {risk && (
                <RiskPanel
                  risk={risk}
                  onHoverIndicator={(addr) => setHighlightedNode(addr)}
                />
              )}
            </div>
            <div className="col-span-4 md:col-span-5">
              <AddToCase address={address} attribution={attribution} />
            </div>
          </BentoGrid>
        </div>
      )}

      {focusedNode && (
        <NodeFocusDrawer address={focusedNode} onClose={() => setFocusedNode(null)} />
      )}
    </div>
  );
}
