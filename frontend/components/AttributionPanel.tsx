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

/** Signed TreeSHAP contribution rendered around a centre axis. */
function SignedBar({ weight, scale }: { weight: number; scale: number }) {
  const frac = scale > 0 ? Math.min(Math.abs(weight) / scale, 1) : 0;
  const positive = weight >= 0;
  return (
    <div className="relative h-1.5 w-24 rounded-full bg-panel2">
      <span className="absolute left-1/2 top-0 h-full w-px bg-border" />
      <span
        className={`absolute top-0 h-full ${positive ? "bg-good" : "bg-bad"}`}
        style={{
          left: positive ? "50%" : `${50 - frac * 50}%`,
          width: `${frac * 50}%`,
        }}
      />
    </div>
  );
}

function EvidenceChain({ candidate }: { candidate: VaspCandidate }) {
  const scale = Math.max(1e-6, ...candidate.evidence.map((e) => Math.abs(e.weight)));
  if (candidate.evidence.length === 0) {
    return <p className="pl-9 text-xs text-muted">No evidence signals fired.</p>;
  }
  return (
    <ol className="relative mt-3 space-y-3 pl-9">
      {/* chain-of-custody spine */}
      <span className="absolute left-[13px] top-1 h-[calc(100%-0.5rem)] w-px bg-border" />
      {candidate.evidence.map((ev, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[30px] top-1 h-2.5 w-2.5 rounded-full border border-accent/60 bg-bg" />
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <Pill tone="accent">
              {SIGNAL_LABEL[ev.signal_type] ?? ev.signal_type}
            </Pill>
            <SignedBar weight={ev.weight} scale={scale} />
            <span className="text-[10px] tabular-nums text-muted">
              {ev.weight >= 0 ? "+" : ""}
              {ev.weight.toFixed(3)}
            </span>
          </div>
          <p className="text-[13px] leading-snug text-text">{ev.description}</p>
          {ev.tx_hashes.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5">
              {ev.tx_hashes.slice(0, 6).map((h) => (
                <span key={h} className="text-[10px] text-muted">
                  {shortAddr(h, 8, 6)}
                </span>
              ))}
              {ev.tx_hashes.length > 6 && (
                <span className="text-[10px] text-muted">
                  +{ev.tx_hashes.length - 6}
                </span>
              )}
            </div>
          )}
          {ev.timestamps.length > 0 && (
            <div className="mt-0.5 text-[10px] text-muted">
              {fmtTime(ev.timestamps[0])}
              {ev.timestamps.length > 1 &&
                ` → ${fmtTime(ev.timestamps[ev.timestamps.length - 1])}`}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
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
    <div className="border-t border-border py-3 first:border-t-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 text-left"
        aria-expanded={open}
      >
        <span className="w-5 text-muted">{open ? "–" : "+"}</span>
        <span className="w-36 truncate font-display font-semibold text-vasp">
          {candidate.vasp_name}
        </span>
        <div className="flex-1">
          <Bar value={candidate.probability} tone={tone} threshold={threshold} />
        </div>
        <span className={`w-16 text-right font-display tabular-nums text-${tone}`}>
          {pct(candidate.probability, 1)}
        </span>
      </button>
      {open && <EvidenceChain candidate={candidate} />}
    </div>
  );
}

export function AttributionPanel({ result }: { result: AttributionResult }) {
  const banner = result.insufficient_evidence
    ? { tone: "warn" as const, label: "INSUFFICIENT EVIDENCE" }
    : result.ambiguous
      ? { tone: "accent" as const, label: "AMBIGUOUS" }
      : { tone: "good" as const, label: "ATTRIBUTED" };

  const top = result.candidates[0];
  const topTone = top ? toneForProb(top.probability, result.confidence_threshold) : "muted";

  return (
    <Panel title="Attribution" right={<Pill tone={banner.tone}>{banner.label}</Pill>}>
      {/* Signature: the calibrated attribution readout. */}
      <div className="rounded-md border border-border bg-panel2 p-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest2 text-muted">
              {result.insufficient_evidence
                ? "no confident attribution"
                : "most likely VASP"}
            </div>
            <div className="mt-1 font-display text-2xl font-semibold text-text">
              {top ? top.vasp_name : "—"}
            </div>
          </div>
          <div className={`font-display text-4xl font-bold tabular-nums text-${topTone}`}>
            {top ? pct(top.probability, 1) : "—"}
          </div>
        </div>

        <div className="mt-3">
          <Bar
            value={top ? top.probability : 0}
            tone={topTone}
            threshold={result.confidence_threshold}
            height="h-3"
          />
          <div className="mt-1 flex justify-between text-[10px] text-muted">
            <span>calibrated probability</span>
            <span>│ threshold {pct(result.confidence_threshold, 0)}</span>
          </div>
        </div>

        {result.explanation && (
          <p className="mt-3 border-t border-border pt-2 text-xs text-muted">
            {result.explanation}
          </p>
        )}
      </div>

      {/* Candidate breakdown + evidence chain. */}
      {result.candidates.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          No candidate VASP reachable from this wallet within bounds.
        </p>
      ) : (
        <div className="mt-2">
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

      <div className="mt-3 flex items-center justify-between border-t border-border pt-2 text-[10px] uppercase tracking-widest text-muted">
        <span>model · {result.model_version}</span>
        <span>no LLM in attribution path</span>
      </div>
    </Panel>
  );
}
