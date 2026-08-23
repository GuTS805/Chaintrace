"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CaseOut } from "@/lib/types";
import { Panel, Pill } from "@/components/ui";
import { fmtTime } from "@/lib/format";

export default function CasesPage() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [name, setName] = useState("");
  const [investigator, setInvestigator] = useState("");
  const [error, setError] = useState<string | null>(null);

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
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-base font-semibold">Cases</h1>

      <Panel title="New case">
        <form onSubmit={create} className="flex flex-wrap gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Case name"
            className="min-w-[200px] flex-1 rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
          />
          <input
            value={investigator}
            onChange={(e) => setInvestigator(e.target.value)}
            placeholder="Investigator (optional)"
            className="min-w-[160px] rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
          />
          <button
            type="submit"
            className="rounded border border-accent/50 bg-accent/10 px-4 py-2 text-accent hover:bg-accent/20"
          >
            create
          </button>
        </form>
      </Panel>

      {error && <p className="text-sm text-bad">{error}</p>}

      <Panel title={`Open cases (${cases.length})`}>
        {cases.length === 0 ? (
          <p className="text-sm text-muted">No cases yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {cases.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/cases/${c.id}`}
                  className="flex items-center gap-3 py-2.5 hover:bg-panel2"
                >
                  <span className="text-muted">#{c.id}</span>
                  <span className="font-semibold text-text">{c.name}</span>
                  <Pill tone="accent">{c.status}</Pill>
                  <span className="ml-auto text-xs text-muted">
                    {fmtTime(c.created_at)}
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
