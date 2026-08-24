"use client";

import { useMemo, useState } from "react";
import type { AttributionResult, Evidence, VaspCandidate } from "@/lib/types";
import { pct, shortAddr, SIGNAL_LABEL, fmtTime } from "@/lib/format";
import { Bar, Panel, Pill, GhostButton } from "./ui";

function toneForProb(p: number, threshold: number): "good" | "warn" | "muted" {
  if (p >= threshold) return "good";
  if (p >= threshold - 0.1) return "warn";
  return "muted";
}

interface Row {
  vasp: string;
  evidence: Evidence;
}

function SignedBar({ weight, scale }: { weight: number; scale: number }) {
  const frac = scale > 0 ? Math.min(Math.abs(weight) / scale, 1) : 0;
  const positive = weight >= 0;
  return (
    <div className="relative h-1.5 w-20 shrink-0 rounded-full bg-panel3">
      <span className="absolute left-1/2 top-0 h-full w-px bg-border" />
      <span
        className={`absolute top-0 h-full rounded-full ${positive ? "bg-good" : "bg-bad"}`}
        style={{
          left: positive ? "50%" : `${50 - frac * 50}%`,
          width: `${frac * 50}%`,
        }}
      />
    </div>
  );
}

function EvidenceRow({
  row,
  scale,
  multiCandidate,
  onHover,
}: {
  row: Row;
  scale: number;
  multiCandidate: boolean;
  onHover: (txHashes: string[] | null) => void;
}) {
  const { evidence: ev } = row;
  return (
    <li
      onMouseEnter={() => ev.tx_hashes.length > 0 && onHover(ev.tx_hashes)}
      onMouseLeave={() => onHover(null)}
      className="group rounded border border-transparent px-3 py-2.5 transition-colors hover:border-accent/30 hover:bg-panel2"
    >
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <Pill tone="accent">{SIGNAL_LABEL[ev.signal_type] ?? ev.signal_type}</Pill>
        {multiCandidate && <Pill tone="gold">{row.vasp}</Pill>}
        <SignedBar weight={ev.weight} scale={scale} />
        <span className="text-[10px] tabular-nums text-muted">
          {ev.weight >= 0 ? "+" : ""}
          {ev.weight.toFixed(3)}
        </span>
        {ev.tx_hashes.length > 0 && (
          <span className="ml-auto text-[10px] text-dim opacity-0 transition-opacity group-hover:opacity-100">
            ↦ highlighted in graph
          </span>
        )}
      </div>
      <p className="text-[13px] leading-snug text-text">{ev.description}</p>
      {ev.tx_hashes.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5">
          {ev.tx_hashes.slice(0, 6).map((h) => (
            <span key={h} className="font-mono text-[10px] text-muted">
              {shortAddr(h, 8, 6)}
            </span>
          ))}
          {ev.tx_hashes.length > 6 && (
            <span className="text-[10px] text-dim">+{ev.tx_hashes.length - 6}</span>
          )}
        </div>
      )}
      {ev.timestamps.length > 0 && (
        <div className="mt-0.5 text-[10px] text-dim">
          {fmtTime(ev.timestamps[0])}
          {ev.timestamps.length > 1 && ` → ${fmtTime(ev.timestamps[ev.timestamps.length - 1])}`}
        </div>
      )}
    </li>
  );
}

export function AttributionPanel({
  result,
  onHoverEvidence,
}: {
  result: AttributionResult;
  onHoverEvidence: (txHashes: string[] | null) => void;
}) {
  const [filter, setFilter] = useState<string | "all">("all");

  const banner = result.insufficient_evidence
    ? { tone: "warn" as const, label: "INSUFFICIENT EVIDENCE" }
    : result.ambiguous
      ? { tone: "accent" as const, label: "AMBIGUOUS" }
      : { tone: "good" as const, label: "ATTRIBUTED" };

  const top = result.candidates[0];
  const topTone = top ? toneForProb(top.probability, result.confidence_threshold) : "muted";
  const multiCandidate = result.candidates.length > 1;

  const rows: Row[] = useMemo(() => {
    const all: Row[] = [];
    for (const c of result.candidates) {
      for (const ev of c.evidence) all.push({ vasp: c.vasp_name, evidence: ev });
    }
    all.sort((a, b) => Math.abs(b.evidence.weight) - Math.abs(a.evidence.weight));
    return filter === "all" ? all : all.filter((r) => r.vasp === filter);
  }, [result.candidates, filter]);

  const scale = Math.max(1e-6, ...rows.map((r) => Math.abs(r.evidence.weight)));

  return (
    <Panel title="Attribution" right={<Pill tone={banner.tone}>{banner.label}</Pill>}>
      {/* Signature: the calibrated attribution readout. */}
      <div className="rounded-md border border-border bg-panel2 p-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted">
              {result.insufficient_evidence ? "no confident attribution" : "most likely VASP"}
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
          <Bar value={top ? top.probability : 0} tone={topTone} threshold={result.confidence_threshold} height="h-3" />
          <div className="mt-1 flex justify-between text-[10px] text-muted">
            <span>calibrated probability</span>
            <span>│ threshold {pct(result.confidence_threshold, 0)}</span>
          </div>
        </div>

        {result.explanation && (
          <p className="mt-3 border-t border-border pt-2 text-xs text-muted">{result.explanation}</p>
        )}
      </div>

      {/* Candidate filter chips (only meaningful with >1 candidate). */}
      {multiCandidate && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-widest text-dim">evidence for</span>
          <GhostButton active={filter === "all"} onClick={() => setFilter("all")}>
            all
          </GhostButton>
          {result.candidates.map((c: VaspCandidate) => (
            <GhostButton key={c.vasp_name} active={filter === c.vasp_name} onClick={() => setFilter(c.vasp_name)}>
              {c.vasp_name} {pct(c.probability, 0)}
            </GhostButton>
          ))}
        </div>
      )}

      {/* Combined, weight-ranked evidence stream — hover to trace it in the
          graph, instead of per-candidate accordions the investigator has to
          open and mentally diff. */}
      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No evidence signals fired for any candidate.</p>
      ) : (
        <ul className="mt-3 max-h-[420px] space-y-1 overflow-y-auto pr-1">
          {rows.map((row, i) => (
            <EvidenceRow
              key={`${row.vasp}-${row.evidence.signal_type}-${i}`}
              row={row}
              scale={scale}
              multiCandidate={multiCandidate}
              onHover={onHoverEvidence}
            />
          ))}
        </ul>
      )}

      <div className="mt-3 flex items-center justify-between border-t border-border pt-2 text-[10px] uppercase tracking-widest text-muted">
        <span>model · {result.model_version}</span>
        <span>no LLM in attribution path</span>
      </div>
    </Panel>
  );
}
