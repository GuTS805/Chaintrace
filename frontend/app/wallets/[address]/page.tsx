"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AttributionResult, GraphResult, RiskResult } from "@/lib/types";
import { AttributionPanel } from "@/components/AttributionPanel";
import { RiskPanel } from "@/components/RiskPanel";
import { GraphView } from "@/components/GraphView";
import { AddToCase } from "@/components/AddToCase";
import { WalletSearch } from "@/components/WalletSearch";
import { Panel } from "@/components/ui";

export default function WalletPage({
  params,
}: {
  params: { address: string };
}) {
  const address = decodeURIComponent(params.address).toLowerCase();
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      api.attribution(address),
      api.risk(address),
      api.graph(address, 5),
    ]).then((results) => {
      if (!active) return;
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
    });
    return () => {
      active = false;
    };
  }, [address]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-base font-semibold">
          <span className="text-muted">wallet</span>{" "}
          <span className="break-all text-accent">{address}</span>
        </h1>
        <a
          href={`${api.base}/wallets/${address}/report`}
          target="_blank"
          rel="noreferrer"
          className="rounded border border-border px-3 py-2 text-xs text-muted hover:border-accent hover:text-accent"
        >
          ↓ report (PDF)
        </a>
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

      {!loading && !error && (
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
