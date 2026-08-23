"use client";

import { useState } from "react";
import type { AttributionResult, VaspCandidate } from "@/lib/types";
import { pct, shortAddr, SIGNAL_LABEL, fmtTime } from "@/lib/format";
import { Bar, Panel, Pill } from "./ui";

function toneForProb(p: number, threshold: number): string {
  if (p >= threshold) return "good";
  if (p >= threshold - 0.1) return "warn";
  return "muted";
}

function CandidateRow({
  candidate,
  threshold,
  rank,
}: {
  candidate: VaspCandidate;
  threshold: number;
  rank: number;
}) {
  const [open, setOpen] = useState(rank === 0);
  const tone = toneForProb(candidate.probability, threshold);
  return (
    <div className="border-b border-border py-3 last:border-b-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 text-left"
      >
        <span className="w-6 text-muted">{open ? "▾" : "▸"}</span>
        <span className="w-40 truncate font-semibold text-vasp">
          {candidate.vasp_name}
        </span>
        <div className="flex-1">
          <Bar value={candidate.probability} tone={tone} />
        </div>
        <span className={`w-14 text-right tabular-nums text-${tone}`}>
          {pct(candidate.probability, 1)}
        </span>
      </button>

      {open && (
        <ul className="mt-3 space-y-2 pl-9">
          {candidate.evidence.length === 0 && (
            <li className="text-xs text-muted">No evidence signals fired.</li>
          )}
          {candidate.evidence.map((ev, i) => (
            <li
              key={i}
              className="rounded border border-border bg-panel2 px-3 py-2"
            >
              <div className="mb-1 flex items-center gap-2">
                <Pill tone="accent">{SIGNAL_LABEL[ev.signal_type] ?? ev.signal_type}</Pill>
                <span className="text-[11px] text-muted">
                  contribution {ev.weight >= 0 ? "+" : ""}
                  {ev.weight.toFixed(3)}
                </span>
              </div>
              <p className="text-text">{ev.description}</p>
              {ev.tx_hashes.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {ev.tx_hashes.slice(0, 6).map((h) => (
                    <span key={h} className="text-[10px] text-muted">
                      {shortAddr(h, 8, 6)}
                    </span>
                  ))}
                  {ev.tx_hashes.length > 6 && (
                    <span className="text-[10px] text-muted">
                      +{ev.tx_hashes.length - 6} more
                    </span>
                  )}
                </div>
              )}
              {ev.timestamps.length > 0 && (
                <div className="mt-1 text-[10px] text-muted">
                  {fmtTime(ev.timestamps[0])}
                  {ev.timestamps.length > 1 &&
                    ` … ${fmtTime(ev.timestamps[ev.timestamps.length - 1])}`}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function AttributionPanel({ result }: { result: AttributionResult }) {
  const banner = result.insufficient_evidence
    ? { tone: "warn" as const, label: "INSUFFICIENT EVIDENCE" }
    : result.ambiguous
      ? { tone: "vasp" as const, label: "AMBIGUOUS" }
      : { tone: "good" as const, label: "ATTRIBUTED" };

  return (
    <Panel
      title="Attribution"
      right={<Pill tone={banner.tone}>{banner.label}</Pill>}
    >
      {result.explanation && (
        <p className="mb-3 rounded border border-border bg-panel2 px-3 py-2 text-xs text-muted">
          {result.explanation}
        </p>
      )}

      {result.candidates.length === 0 ? (
        <p className="text-sm text-muted">
          No candidate VASP reachable from this wallet within bounds.
        </p>
      ) : (
        <div>
          {result.candidates.map((c, i) => (
            <CandidateRow
              key={c.vasp_name}
              candidate={c}
              threshold={result.confidence_threshold}
              rank={i}
            />
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-[10px] text-muted">
        <span>model {result.model_version}</span>
        <span>threshold {pct(result.confidence_threshold)}</span>
      </div>
    </Panel>
  );
}
