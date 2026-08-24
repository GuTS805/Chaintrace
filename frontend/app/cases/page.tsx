"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CaseOut, CaseStatus } from "@/lib/types";
import { Panel, Pill } from "@/components/ui";
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
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <div className="text-[11px] uppercase tracking-widest text-accent">
          investigation workspace
        </div>
        <h1 className="mt-1 font-display text-2xl font-semibold text-text">Cases</h1>
        <p className="mt-1 text-xs text-muted">
          Group wallets, evidence, and notes under a case for reporting and disclosure.
        </p>
      </div>

      <Panel title="Open a case">
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
      </Panel>

      {error && <p className="text-sm text-bad">{error}</p>}

      <Panel title={`Open cases (${cases.length})`} bodyClassName="p-0">
        {cases.length === 0 ? (
          <p className="p-4 text-sm text-muted">
            No cases yet. Open one above, then pin wallets to it from any
            investigation to start building a disclosure-ready record.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {cases.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/cases/${c.id}`}
                  className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-panel2"
                >
                  <span className="font-mono text-xs text-dim">{caseRef(c.id)}</span>
                  <span className="font-display font-semibold text-text">{c.name}</span>
                  <Pill tone={STATUS_TONE[c.status]}>{c.status}</Pill>
                  {c.investigator && (
                    <span className="text-xs text-muted">· {c.investigator}</span>
                  )}
                  <span className="ml-auto text-xs text-dim">{fmtTime(c.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
