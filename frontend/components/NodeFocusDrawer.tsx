"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AttributionResult, RiskResult } from "@/lib/types";
import { pct, shortAddr } from "@/lib/format";
import { Bar, Pill } from "./ui";

const LEVEL_TONE: Record<string, "muted" | "warn" | "bad"> = {
  LOW: "muted",
  MEDIUM: "warn",
  HIGH: "bad",
  CRITICAL: "bad",
};

/** Clicking a non-root graph node opens this instead of a hard page
 * navigation — the investigator stays inside the current investigation and
 * only "opens" the new wallet as its own page if they deliberately choose to
 * (research finding: professional tools keep the graph as the surface you
 * stay inside, not something that navigates you away). */
export function NodeFocusDrawer({ address, onClose }: { address: string; onClose: () => void }) {
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.allSettled([api.attribution(address), api.risk(address)]).then((results) => {
      if (!active) return;
      const [a, r] = results;
      if (a.status === "fulfilled") setAttribution(a.value);
      if (r.status === "fulfilled") setRisk(r.value);
      if (a.status === "rejected" && r.status === "rejected") setError("Could not load this wallet.");
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [address]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const top = attribution?.candidates[0];

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-bg/60 backdrop-blur-[2px]" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-sm flex-col border-l border-borderStrong bg-panel shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-dim">inspecting</div>
            <div className="font-mono text-xs text-text">{shortAddr(address, 10, 8)}</div>
          </div>
          <button
            onClick={onClose}
            className="rounded border border-border px-2 py-1 text-xs text-muted hover:border-accent/40 hover:text-accent"
          >
            close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && <p className="text-sm text-muted">Loading…</p>}
          {error && <p className="text-sm text-bad">{error}</p>}

          {!loading && attribution && (
            <div className="space-y-4">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-dim">attribution</div>
                {top ? (
                  <>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="font-display text-lg font-semibold text-gold">{top.vasp_name}</span>
                      <span className="font-display text-xl font-bold text-good">{pct(top.probability, 1)}</span>
                    </div>
                    <Bar value={top.probability} tone="good" threshold={attribution.confidence_threshold} height="h-2" />
                  </>
                ) : (
                  <p className="mt-1 text-sm text-muted">
                    {attribution.insufficient_evidence ? "Insufficient evidence." : "No candidate."}
                  </p>
                )}
              </div>

              {risk && (
                <div>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-[10px] uppercase tracking-widest text-dim">risk</span>
                    <Pill tone={LEVEL_TONE[risk.level] ?? "muted"}>{risk.level}</Pill>
                  </div>
                  {risk.indicators.length > 0 ? (
                    <ul className="space-y-1">
                      {risk.indicators.slice(0, 3).map((ind, i) => (
                        <li key={i} className="text-xs text-muted">
                          <Pill tone="bad">{ind.category}</Pill> {ind.description}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-muted">No exposure detected.</p>
                  )}
                </div>
              )}

              {top && top.evidence.length > 0 && (
                <div>
                  <div className="mb-1 text-[10px] uppercase tracking-widest text-dim">top evidence</div>
                  <ul className="space-y-1.5">
                    {top.evidence.slice(0, 3).map((ev, i) => (
                      <li key={i} className="text-xs text-text">
                        {ev.description}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-border p-4">
          <Link
            href={`/wallets/${address}`}
            className="block rounded border border-accent/50 bg-accent/10 px-3 py-2 text-center text-xs uppercase tracking-widest text-accent hover:bg-accent/20"
          >
            open full investigation ↗
          </Link>
        </div>
      </div>
    </div>
  );
}
