"use client";

import { useMemo, useState } from "react";
import type { EvidenceBundle } from "@/lib/types";
import { fmtTime, shortAddr, SIGNAL_LABEL } from "@/lib/format";
import { Panel, Pill } from "./ui";

/**
 * The flat evidence records exactly as they were hashed.
 *
 * This is the citable form: one row per observed transaction, each carrying its
 * own content-derived id, so a reviewer can reference a single line rather than
 * "the deposit-sweep signal". The grouped, readable view lives in the
 * attribution panel; this is the ledger behind it.
 */
export function EvidenceLedger({ bundle }: { bundle: EvidenceBundle }) {
  const [signal, setSignal] = useState<string>("ALL");

  const signals = useMemo(
    () => Array.from(new Set(bundle.records.map((r) => r.signal_type))).sort(),
    [bundle.records],
  );

  const rows = useMemo(
    () =>
      signal === "ALL"
        ? bundle.records
        : bundle.records.filter((r) => r.signal_type === signal),
    [bundle.records, signal],
  );

  return (
    <Panel
      title="Evidence ledger"
      right={
        <span className="text-[10px] tabular-nums text-muted">
          {rows.length}/{bundle.record_count} records
        </span>
      }
    >
      <div className="mb-3 flex flex-wrap gap-1.5">
        {["ALL", ...signals].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSignal(s)}
            className={`rounded border px-2 py-1 text-[10px] uppercase tracking-wider transition-colors ${
              signal === s
                ? "border-accent/60 text-accent"
                : "border-border text-muted hover:border-accent/40 hover:text-text"
            }`}
          >
            {s === "ALL" ? "all" : (SIGNAL_LABEL[s] ?? s)}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left">
          <thead>
            <tr className="border-b border-border text-[10px] uppercase tracking-wider text-muted">
              <th className="py-2 pr-3 font-normal">record</th>
              <th className="py-2 pr-3 font-normal">signal</th>
              <th className="py-2 pr-3 font-normal">transaction</th>
              <th className="py-2 pr-3 font-normal">counterparty</th>
              <th className="py-2 pr-3 font-normal">observed</th>
              <th className="py-2 pr-3 text-right font-normal">weight</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.evidence_id}
                className="border-b border-border/50 align-top hover:bg-panel2"
              >
                <td className="py-2 pr-3">
                  <code className="text-[10px] text-muted">{r.evidence_id}</code>
                </td>
                <td className="py-2 pr-3">
                  <Pill tone="accent">
                    {SIGNAL_LABEL[r.signal_type] ?? r.signal_type}
                  </Pill>
                </td>
                <td className="py-2 pr-3">
                  {r.source_transaction ? (
                    <code className="text-[11px] text-text">
                      {shortAddr(r.source_transaction, 10, 6)}
                    </code>
                  ) : (
                    // A label-based signal rests on a label source, not a
                    // transfer. It is still hashed, so it is still shown.
                    <span className="text-[11px] text-muted">no transaction</span>
                  )}
                </td>
                <td className="py-2 pr-3">
                  {r.target_wallet ? (
                    <code className="text-[11px] text-vasp">
                      {shortAddr(r.target_wallet, 8, 6)}
                    </code>
                  ) : (
                    <span className="text-[11px] text-muted">—</span>
                  )}
                </td>
                <td className="py-2 pr-3 text-[11px] tabular-nums text-muted">
                  {r.observed_at ? fmtTime(r.observed_at) : "—"}
                </td>
                <td className="py-2 pr-3 text-right text-[11px] tabular-nums">
                  <span className={r.weight >= 0 ? "text-good" : "text-bad"}>
                    {r.weight >= 0 ? "+" : ""}
                    {r.weight.toFixed(3)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && (
        <p className="pt-3 text-[13px] text-muted">
          No evidence records for this filter.
        </p>
      )}
    </Panel>
  );
}
