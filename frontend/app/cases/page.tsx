"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CaseOut, CaseStatus } from "@/lib/types";
import { BentoGrid, Button, Eyebrow, Tile, Pill } from "@/components/ui";
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
    <div className="space-y-12">
      {/* Page header */}
      <div>
        <Eyebrow tone="accent">Investigation workspace</Eyebrow>
        <h1 className="mt-2 font-display text-[26px] font-bold tracking-tight text-heading">Cases</h1>
        <p className="mt-2 text-[16px] text-body">
          Group wallets, evidence, and notes under a case for reporting and disclosure.
        </p>
      </div>

      {/* Open a case panel */}
      <Tile bodyClassName="p-8">
        <Eyebrow className="mb-4">Open a case</Eyebrow>
        <form onSubmit={create} className="flex flex-wrap gap-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Case name, e.g. &ldquo;Ransomware payout — Q1&rdquo;"
            className="h-[52px] min-w-[220px] flex-1 rounded-input border border-soft-border bg-surface-lavender px-4 text-sm text-heading outline-none placeholder:text-muted transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
          <input
            value={investigator}
            onChange={(e) => setInvestigator(e.target.value)}
            placeholder="Investigator (optional)"
            className="h-[52px] w-[220px] rounded-input border border-soft-border bg-surface-lavender px-4 text-sm text-heading outline-none placeholder:text-muted transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
          <Button type="submit" variant="primary" disabled={creating || !name.trim()}>
            {creating ? "Opening…" : "Open case"}
          </Button>
        </form>
      </Tile>

      {error && (
        <p className="text-sm text-bad-text">{error}</p>
      )}

      {/* Open cases */}
      <div>
        <div className="flex items-center gap-3 pb-6">
          <Eyebrow>Open cases ({cases.length})</Eyebrow>
          <span className="h-px flex-1 bg-soft-border" />
        </div>

        {cases.length === 0 ? (
          <Tile bodyClassName="p-8">
            <div className="flex flex-col items-center text-center">
              {/* Empty state illustration */}
              <div className="mb-4 flex h-[120px] w-[120px] items-center justify-center rounded-full bg-primary-soft">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
                  <rect x="10" y="14" width="28" height="24" rx="4" stroke="#F2A93B" strokeWidth="2" fill="#2E230F" />
                  <path d="M10 22h28" stroke="#F2A93B" strokeWidth="2" />
                  <circle cx="24" cy="32" r="4" fill="#BBA9F5" />
                  <path d="M24 28v8M20 32h8" stroke="#F2A93B" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </div>
              <p className="text-[14px] text-body">
                No cases yet. Open one above, then pin wallets to it from any
                investigation to start building a disclosure-ready record.
              </p>
            </div>
          </Tile>
        ) : (
          <BentoGrid>
            {cases.map((c) => (
              <Tile key={c.id} interactive className="col-span-4" bodyClassName="p-6">
                <Link href={`/cases/${c.id}`} className="flex h-full flex-col">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase text-muted">{caseRef(c.id)}</span>
                    <Pill tone={STATUS_TONE[c.status]}>{c.status}</Pill>
                  </div>
                  <div className="mt-4 font-display text-[20px] font-semibold text-heading">{c.name}</div>
                  {c.investigator && (
                    <div className="mt-1 text-xs text-muted">{c.investigator}</div>
                  )}
                  <div className="mt-auto pt-3 text-[11px] text-muted">{fmtTime(c.created_at)}</div>
                </Link>
              </Tile>
            ))}
          </BentoGrid>
        )}
      </div>
    </div>
  );
}
