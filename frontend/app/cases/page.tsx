"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CaseOut, CaseStatus } from "@/lib/types";
import { BentoGrid, Tile, Pill } from "@/components/ui";
import { fmtTime } from "@/lib/format";

const STATUS_TONE: Record<CaseStatus, "good" | "warn" | "muted"> = {
  OPEN: "good",
  IN_REVIEW: "warn",
  CLOSED: "muted",
};

function caseRef(id: number): string {
  return `CT-${String(id).padStart(4, "0")}`;
}

export default function CasesPage() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [name, setName] = useState("");
  const [investigator, setInvestigator] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  function load() {
    api
      .listCases()
      .then(setCases)
      .catch((e) => setError(String(e)));
  }

  useEffect(load, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createCase({
        name: name.trim(),
        investigator: investigator.trim() || undefined,
      });
      setName("");
      setInvestigator("");
      load();
    } catch (err) {
      setError(String(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <BentoGrid>
      <div className="col-span-4 md:col-span-12">
        <div className="text-[11px] uppercase tracking-widest text-accent">
          investigation workspace
        </div>
        <h1 className="mt-1 font-display text-2xl font-semibold text-text">Cases</h1>
        <p className="mt-1 text-xs text-muted">
          Group wallets, evidence, and notes under a case for reporting and disclosure.
        </p>
      </div>

      <Tile title="Open a case" className="col-span-4 md:col-span-12">
        <form onSubmit={create} className="flex flex-wrap gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Case name, e.g. &ldquo;Ransomware payout — Q1&rdquo;"
            className="min-w-[220px] flex-1 rounded border border-border bg-panel2 px-3 py-2 text-sm text-text outline-none placeholder:text-dim focus:border-accent"
          />
          <input
            value={investigator}
            onChange={(e) => setInvestigator(e.target.value)}
            placeholder="Investigator (optional)"
            className="min-w-[160px] rounded border border-border bg-panel2 px-3 py-2 text-sm text-text outline-none placeholder:text-dim focus:border-accent"
          />
          <button
            type="submit"
            disabled={creating || !name.trim()}
            className="rounded border border-accent/50 bg-accent/10 px-4 py-2 text-xs uppercase tracking-widest text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {creating ? "opening…" : "open case"}
          </button>
        </form>
      </Tile>

      {error && (
        <div className="col-span-4 md:col-span-12">
          <p className="text-sm text-bad">{error}</p>
        </div>
      )}

      <div className="col-span-4 flex items-center gap-3 py-1 md:col-span-12">
        <span className="text-[10px] uppercase tracking-widest text-muted">
          open cases ({cases.length})
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      {cases.length === 0 ? (
        <Tile className="col-span-4 md:col-span-12">
          <p className="text-sm text-muted">
            No cases yet. Open one above, then pin wallets to it from any
            investigation to start building a disclosure-ready record.
          </p>
        </Tile>
      ) : (
        cases.map((c) => (
          <Tile key={c.id} interactive className="col-span-4 md:col-span-4">
            <Link href={`/cases/${c.id}`} className="flex h-full flex-col">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-dim">{caseRef(c.id)}</span>
                <Pill tone={STATUS_TONE[c.status]}>{c.status}</Pill>
              </div>
              <div className="mt-2 font-display font-semibold text-text">{c.name}</div>
              {c.investigator && (
                <div className="mt-1 text-xs text-muted">{c.investigator}</div>
              )}
              <div className="mt-auto pt-3 text-[11px] text-dim">{fmtTime(c.created_at)}</div>
            </Link>
          </Tile>
        ))
      )}
    </BentoGrid>
  );
}
