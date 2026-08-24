"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import * as Dialog from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import { ArrowUpRight, Search, ShieldAlert, X } from "lucide-react";
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
 * only "opens" the new wallet as its own page if they deliberately choose to. */
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

  const top = attribution?.candidates[0];

  // Exit animation plays via the AnimatePresence wrapping this component's
  // conditional render at the call site (wallets/[address]/page.tsx) — this
  // component only supplies the motion values.
  return (
    <Dialog.Root open onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal forceMount>
        <Dialog.Overlay asChild forceMount>
          <motion.div
            className="fixed inset-0 z-40 bg-black/55 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          />
        </Dialog.Overlay>
        <Dialog.Content asChild forceMount>
          <motion.div
            className="fixed inset-y-0 right-0 z-40 flex h-full w-full max-w-sm flex-col border-l border-soft-border bg-surface shadow-card-hover"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
          >
              <div className="flex items-center justify-between border-b border-soft-border px-5 py-4">
                <div className="flex items-center gap-2.5">
                  <Search size={15} className="text-primary" />
                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-muted">Inspecting</div>
                    <div className="font-mono text-xs text-heading">{shortAddr(address, 10, 8)}</div>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    className="rounded-btn p-1.5 text-muted hover:bg-surface-lavender hover:text-heading"
                    aria-label="Close"
                  >
                    <X size={16} />
                  </button>
                </Dialog.Close>
              </div>

              <div className="flex-1 overflow-y-auto p-5">
                {loading && <p className="text-sm text-muted">Loading…</p>}
                {error && <p className="text-sm text-bad-text">{error}</p>}

                {!loading && attribution && (
                  <div className="space-y-5">
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-muted">Attribution</div>
                      {top ? (
                        <>
                          <div className="mt-1 flex items-baseline justify-between">
                            <span className="font-display text-lg font-semibold text-primary">{top.vasp_name}</span>
                            <span className="font-display text-xl font-bold text-good-text">
                              {pct(top.probability, 1)}
                            </span>
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
                        <div className="mb-1.5 flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-muted">
                            {risk.flagged && <ShieldAlert size={13} className="text-bad-text" />}
                            Risk
                          </span>
                          <Pill tone={LEVEL_TONE[risk.level] ?? "muted"}>{risk.level}</Pill>
                        </div>
                        {risk.indicators.length > 0 ? (
                          <ul className="space-y-1.5">
                            {risk.indicators.slice(0, 3).map((ind, i) => (
                              <li key={i} className="flex items-start gap-2 text-xs text-body">
                                <Pill tone="bad" className="mt-0.5 shrink-0">{ind.category}</Pill>
                                <span>{ind.description}</span>
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
                        <div className="mb-1.5 text-[10px] uppercase tracking-widest text-muted">Top evidence</div>
                        <ul className="space-y-1.5">
                          {top.evidence.slice(0, 3).map((ev, i) => (
                            <li key={i} className="text-xs text-heading">
                              {ev.description}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="border-t border-soft-border p-4">
                <Link
                  href={`/wallets/${address}`}
                  className="flex items-center justify-center gap-1.5 rounded-btn bg-primary-soft px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-widest text-primary transition-colors hover:bg-primary/10"
                >
                  Open full investigation
                  <ArrowUpRight size={14} />
                </Link>
              </div>
            </motion.div>
          </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
