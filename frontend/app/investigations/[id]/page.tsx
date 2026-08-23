"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type {
  EvidenceBundle,
  GraphResult,
  InvestigationDetail,
} from "@/lib/types";
import { isTerminal } from "@/lib/types";
import { AttributionPanel } from "@/components/AttributionPanel";
import { RiskPanel } from "@/components/RiskPanel";
import { GraphView } from "@/components/GraphView";
import { InvestigationProgress } from "@/components/InvestigationProgress";
import { MethodologyPanel } from "@/components/MethodologyPanel";
import { EvidenceLedger } from "@/components/EvidenceLedger";
import { Panel } from "@/components/ui";

const POLL_MS = 1000;

export default function InvestigationPage({
  params,
}: {
  params: { id: string };
}) {
  const id = decodeURIComponent(params.id);
  const [inv, setInv] = useState<InvestigationDetail | null>(null);
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [evidence, setEvidence] = useState<EvidenceBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Poll until the run reaches a terminal state, then stop.
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function tick() {
      try {
        const next = await api.getInvestigation(id);
        if (!active) return;
        setInv(next);
        setError(null);
        if (!isTerminal(next.status)) {
          timer = setTimeout(tick, POLL_MS);
        }
      } catch (e) {
        if (!active) return;
        setError(String(e));
      }
    }

    tick();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id]);

  // The heavy sub-resources exist only once there is a snapshot, so they are
  // fetched after completion rather than polled alongside the status.
  useEffect(() => {
    if (!inv?.has_result) return;
    let active = true;
    Promise.allSettled([
      api.investigationGraph(id),
      api.investigationEvidence(id),
    ]).then(([g, e]) => {
      if (!active) return;
      if (g.status === "fulfilled") setGraph(g.value.graph);
      if (e.status === "fulfilled") setEvidence(e.value);
    });
    return () => {
      active = false;
    };
  }, [id, inv?.has_result]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Panel title="Error">
          <p className="break-words text-[13px] text-bad">{error}</p>
          <p className="mt-2 text-xs text-muted">
            A 404 means no investigation with this id exists.{" "}
            <Link href="/investigations" className="text-accent hover:underline">
              Back to investigations
            </Link>
            .
          </p>
        </Panel>
      </div>
    );
  }

  if (!inv) {
    return <p className="text-[13px] text-muted">Loading investigation…</p>;
  }

  const done = inv.status === "COMPLETED";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-base font-semibold">
          <span className="text-muted">investigation</span>{" "}
          <span className="text-accent">{inv.id}</span>
        </h1>
        <code className="break-all text-[12px] text-text">{inv.address}</code>
        {done && (
          <a
            href={api.investigationReportUrl(inv.id)}
            target="_blank"
            rel="noreferrer"
            className="rounded border border-border px-3 py-2 text-xs text-muted hover:border-accent hover:text-accent"
          >
            ↓ report (PDF)
          </a>
        )}
        <Link
          href="/investigations"
          className="ml-auto text-[11px] uppercase tracking-widest text-muted hover:text-accent"
        >
          all investigations
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <InvestigationProgress
            status={inv.status}
            error={inv.error}
            startedAt={inv.started_at}
            completedAt={inv.completed_at}
          />
          {inv.attribution && <AttributionPanel result={inv.attribution} />}
          {inv.risk && <RiskPanel risk={inv.risk} />}
        </div>
        <div className="space-y-4">
          {inv.methodology && (
            <MethodologyPanel
              method={inv.methodology}
              investigationId={inv.id}
              chain={inv.chain}
            />
          )}
          {graph && <GraphView graph={graph} />}
        </div>
      </div>

      {evidence && <EvidenceLedger bundle={evidence} />}
    </div>
  );
}
