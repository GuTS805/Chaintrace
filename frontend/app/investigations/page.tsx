"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Chain, InvestigationOut } from "@/lib/types";
import { Panel, Pill } from "@/components/ui";
import { DEMO_WALLETS, fmtTime, shortAddr } from "@/lib/format";

const CHAINS: Chain[] = ["ethereum", "polygon", "arbitrum", "base", "bitcoin"];

const STATUS_TONE: Record<string, "muted" | "accent" | "good" | "bad"> = {
  QUEUED: "muted",
  FETCHING: "accent",
  TRAVERSING: "accent",
  ANALYZING: "accent",
  COMPLETED: "good",
  FAILED: "bad",
};

export default function InvestigationsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<InvestigationOut[]>([]);
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState<Chain>("ethereum");
  const [requestedBy, setRequestedBy] = useState("");
  const [depth, setDepth] = useState(6);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function load() {
    api
      .listInvestigations()
      .then(setRows)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, []);

  // Anything still running will change state on its own; refresh while any row
  // is non-terminal so the list does not sit on a stale "TRAVERSING".
  useEffect(() => {
    const pending = rows.some(
      (r) => r.status !== "COMPLETED" && r.status !== "FAILED",
    );
    if (!pending) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [rows]);

  async function open(e: React.FormEvent) {
    e.preventDefault();
    const addr = address.trim();
    if (!addr) return;
    setSubmitting(true);
    setError(null);
    try {
      const inv = await api.createInvestigation({
        address: addr,
        chain,
        depth,
        requested_by: requestedBy.trim() || undefined,
      });
      // Straight to the detail page — that is where progress is watched.
      if (inv) router.push(`/investigations/${inv.id}`);
    } catch (err) {
      setError(String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="space-y-1">
        <h1 className="font-display text-xl font-semibold text-text">
          Investigations
        </h1>
        <p className="text-[13px] text-muted">
          An investigation is a durable record: who asked, against which chain and
          bounds, which model answered, and what was concluded. Results are frozen
          on completion, so a report reprinted later says what it said the day it
          was filed.
        </p>
      </div>

      <Panel title="Open an investigation">
        <form onSubmit={open} className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <select
              value={chain}
              onChange={(e) => setChain(e.target.value as Chain)}
              className="rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
            >
              {CHAINS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="0x… wallet address"
              spellCheck={false}
              className="min-w-[280px] flex-1 rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
            />
            <button
              type="submit"
              disabled={submitting || !address.trim()}
              className="rounded border border-accent/50 bg-accent/10 px-4 py-2 text-accent hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? "opening…" : "open"}
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={requestedBy}
              onChange={(e) => setRequestedBy(e.target.value)}
              placeholder="Investigator (optional)"
              className="min-w-[180px] rounded border border-border bg-panel2 px-3 py-2 text-[13px] outline-none focus:border-accent"
            />
            <label className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted">
              max hops
              <input
                type="number"
                min={1}
                max={8}
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="w-16 rounded border border-border bg-panel2 px-2 py-2 text-center text-[13px] tabular-nums text-text outline-none focus:border-accent"
              />
            </label>
          </div>
        </form>

        <div className="mt-4 border-t border-border pt-3">
          <div className="text-[10px] uppercase tracking-widest text-muted">
            seeded subjects
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {DEMO_WALLETS.map((w) => (
              <button
                key={w.address}
                type="button"
                onClick={() => setAddress(w.address)}
                className="rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent/50 hover:text-accent"
              >
                {w.label}
              </button>
            ))}
          </div>
        </div>
      </Panel>

      {error && (
        <Panel title="Error">
          <p className="break-words text-[13px] text-bad">{error}</p>
          <p className="mt-2 text-xs text-muted">
            A 422 means the address is not valid for the selected chain. Otherwise
            check that the API is running on{" "}
            <code className="text-text">{api.base}</code>.
          </p>
        </Panel>
      )}

      <Panel title={`Investigations (${rows.length})`}>
        {rows.length === 0 ? (
          <p className="text-[13px] text-muted">
            None yet. Open one above — it returns immediately and runs in the
            background.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {rows.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/investigations/${r.id}`}
                  className="flex flex-wrap items-center gap-3 py-2.5 hover:bg-panel2"
                >
                  <code className="text-[12px] text-accent">{r.id}</code>
                  <Pill tone="vasp">{r.chain}</Pill>
                  <code className="text-[12px] text-text">
                    {shortAddr(r.address, 10, 8)}
                  </code>
                  <Pill tone={STATUS_TONE[r.status] ?? "muted"}>{r.status}</Pill>
                  {r.requested_by && (
                    <span className="text-[11px] text-muted">
                      {r.requested_by}
                    </span>
                  )}
                  <span className="ml-auto text-[11px] tabular-nums text-muted">
                    {fmtTime(r.created_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
