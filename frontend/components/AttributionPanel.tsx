"use client";

import { useMemo, useState } from "react";
import type { AttributionResult, Evidence, VaspCandidate } from "@/lib/types";
import { pct, shortAddr, SIGNAL_LABEL, fmtTime } from "@/lib/format";
import { Eyebrow, GhostButton, Pill, Tile } from "./ui";

function toneForProb(p: number, threshold: number): "good" | "warn" | "muted" {
  if (p >= threshold) return "good";
  if (p >= threshold - 0.1) return "warn";
  return "muted";
}

interface Row {
  vasp: string;
  evidence: Evidence;
}

function strengthLabel(weight: number, scale: number): string {
  const frac = scale > 0 ? Math.abs(weight) / scale : 0;
  const sign = weight >= 0 ? "" : "counter-evidence · ";
  if (frac >= 0.66) return `${sign}Very strong`;
  if (frac >= 0.33) return `${sign}Strong`;
  return `${sign}Moderate`;
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
      className="group -mx-6 px-6 py-4 transition-colors hover:bg-panel2"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-text">
            {SIGNAL_LABEL[ev.signal_type] ?? ev.signal_type}
          </span>
          {multiCandidate && <Pill tone="gold">{row.vasp}</Pill>}
        </div>
        <div className="flex items-center gap-3 text-[12px] tabular-nums">
          <span className="text-dim">{strengthLabel(ev.weight, scale)}</span>
          <span className={ev.weight >= 0 ? "text-muted" : "text-bad"}>
            {ev.weight >= 0 ? "+" : ""}
            {ev.weight.toFixed(3)}
          </span>
        </div>
      </div>
      <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{ev.description}</p>
      {ev.tx_hashes.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          {ev.tx_hashes.slice(0, 6).map((h) => (
            <span key={h} className="font-mono text-[11px] text-dim">
              {shortAddr(h, 8, 6)}
            </span>
          ))}
          {ev.tx_hashes.length > 6 && (
            <span className="text-[11px] text-dim">+{ev.tx_hashes.length - 6} more</span>
          )}
          <span className="text-[11px] text-dim opacity-0 transition-opacity group-hover:opacity-100">
            traced in graph ↦
          </span>
        </div>
      )}
      {ev.timestamps.length > 0 && (
        <div className="mt-1 font-mono text-[11px] text-dim">
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
    ? { tone: "warn" as const, label: "Insufficient evidence" }
    : result.ambiguous
      ? { tone: "accent" as const, label: "Ambiguous" }
      : { tone: "good" as const, label: "Attributed" };

  const top = result.candidates[0];
  const topTone = top ? toneForProb(top.probability, result.confidence_threshold) : "muted";
  const multiCandidate = result.candidates.length > 1;
  const confidenceWord =
    top && top.probability >= result.confidence_threshold
      ? "High confidence attribution"
      : top
        ? "Below the confidence threshold"
        : undefined;

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
    <Tile bodyClassName="p-8">
      {/* Verdict — the largest, most visually dominant element on the page. */}
      <div className="flex items-start justify-between gap-6">
        <Eyebrow>
          {result.insufficient_evidence ? "No confident attribution" : "Most likely VASP"}
        </Eyebrow>
        <Pill tone={banner.tone}>{banner.label}</Pill>
      </div>

      <div className="mt-3 flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div className="font-display text-[44px] font-semibold leading-[1.05] tracking-tight text-text">
          {top ? top.vasp_name : "—"}
        </div>
        <div className={`font-display text-[56px] font-semibold leading-none tabular-nums text-${topTone}`}>
          {top ? pct(top.probability, 1) : "—"}
        </div>
      </div>
      {confidenceWord && <p className="mt-1 text-[13px] text-muted">{confidenceWord}</p>}

      <div className="mt-6">
        <div className="h-px w-full overflow-hidden rounded-full bg-panel3">
          <div
            className={`h-full transition-[width] duration-500 ease-out ${
              topTone === "good" ? "bg-good" : topTone === "warn" ? "bg-warn" : "bg-muted"
            }`}
            style={{ width: `${(top ? Math.max(0, Math.min(1, top.probability)) : 0) * 100}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-dim">
          <span>Calibrated probability</span>
          <span>Threshold {pct(result.confidence_threshold, 0)}</span>
        </div>
      </div>

      {result.explanation && (
        <p className="mt-5 max-w-2xl text-[14px] leading-relaxed text-muted">{result.explanation}</p>
      )}

      {/* Evidence — unboxed rows, not cards-inside-a-card. */}
      <div className="mt-10 border-t border-border pt-6">
        <div className="flex items-center justify-between">
          <Eyebrow>Why this attribution?</Eyebrow>
          <span className="text-[11px] text-dim">
            {rows.length} signal{rows.length === 1 ? "" : "s"}
          </span>
        </div>

        {multiCandidate && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
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

        {rows.length === 0 ? (
          <p className="mt-4 text-[13px] text-muted">No evidence signals fired for any candidate.</p>
        ) : (
          <ul className="mt-2 max-h-[440px] divide-y divide-border overflow-y-auto">
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
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-border pt-4 text-[11px] text-dim">
        <span>Model · {result.model_version}</span>
        <span>No LLM in attribution path</span>
      </div>
    </Tile>
  );
}
