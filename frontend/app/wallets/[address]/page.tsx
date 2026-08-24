"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AttributionResult, GraphResult, RiskResult } from "@/lib/types";
import { AttributionPanel } from "@/components/AttributionPanel";
import { RiskPanel } from "@/components/RiskPanel";
import { GraphView } from "@/components/GraphView";
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
  const address = decoded.toLowerCase().startsWith("0x")
    ? decoded.toLowerCase()
    : decoded;
  const chain = address.startsWith("T") ? "TRON" : "ETHEREUM";
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

  // A wallet with no local data: no candidates and an empty graph.
  const isEmpty =
    (attribution?.candidates.length ?? 0) === 0 &&
    (graph?.nodes.length ?? 0) <= 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-base font-semibold">
          <span className="text-muted">wallet</span>{" "}
          <span className="break-all text-accent">{address}</span>{" "}
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
              className="rounded border border-accent/50 bg-accent/10 px-3 py-2 text-xs text-accent hover:bg-accent/20"
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
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="space-y-4">
            {attribution && <AttributionPanel result={attribution} />}
            {risk && <RiskPanel risk={risk} />}
            <AddToCase address={address} attribution={attribution} />
          </div>
          <div>{graph && <GraphView graph={graph} />}</div>
        </div>
      )}
    </div>
  );
}
