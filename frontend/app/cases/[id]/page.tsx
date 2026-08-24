"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CaseDetail, CaseStatus, FindingSeverity } from "@/lib/types";
import { PdfButton } from "@/components/PdfButton";
import { Panel, Pill } from "@/components/ui";
import { fmtTime, shortAddr } from "@/lib/format";

const SEVERITIES: FindingSeverity[] = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"];

const SEV_TONE: Record<FindingSeverity, "muted" | "warn" | "bad"> = {
  INFO: "muted",
  LOW: "muted",
  MEDIUM: "warn",
  HIGH: "bad",
  CRITICAL: "bad",
};

const STATUS_TONE: Record<CaseStatus, "good" | "warn" | "muted"> = {
  OPEN: "good",
  IN_REVIEW: "warn",
  CLOSED: "muted",
};

function caseRef(id: number): string {
  return `CT-${String(id).padStart(4, "0")}`;
}

export default function CaseDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const caseId = Number(params.id);
  const router = useRouter();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [wallet, setWallet] = useState("");
  const [severity, setSeverity] = useState<FindingSeverity>("INFO");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api
      .getCase(caseId)
      .then(setDetail)
      .catch((e) => setError(String(e)));
  }, [caseId]);

  useEffect(load, [load]);

  async function addFinding(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.addFinding(caseId, {
        title: title.trim(),
        wallet_address: wallet.trim() || undefined,
        severity,
        description: note.trim() || undefined,
      });
      setTitle("");
      setWallet("");
      setNote("");
      setSeverity("INFO");
      load();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!confirm("Delete this case? This cannot be undone.")) return;
    await api.deleteCase(caseId);
    router.push("/cases");
  }

  if (error) return <p className="text-sm text-bad">{error}</p>;
  if (!detail) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <Link href="/cases" className="text-xs text-muted hover:text-accent">
          ← cases
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <span className="font-mono text-xs text-dim">{caseRef(detail.id)}</span>
          <h1 className="font-display text-xl font-semibold text-text">{detail.name}</h1>
          <Pill tone={STATUS_TONE[detail.status]}>{detail.status}</Pill>
          <PdfButton
            path={`/cases/${caseId}/report`}
            className="ml-auto rounded border border-border px-2 py-1 text-xs text-muted hover:border-accent hover:text-accent"
          >
            ↓ report (PDF)
          </PdfButton>
          <button
            onClick={remove}
            className="rounded border border-bad/40 px-2 py-1 text-xs text-bad hover:bg-bad/10"
          >
            delete
          </button>
        </div>
        {detail.investigator && (
          <p className="mt-1 text-xs text-muted">investigator: {detail.investigator}</p>
        )}
      </div>

      <Panel title="Add finding / note">
        <form onSubmit={addFinding} className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What did you find?"
              className="min-w-[220px] flex-1 rounded border border-border bg-panel2 px-3 py-2 text-sm text-text outline-none placeholder:text-dim focus:border-accent"
            />
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as FindingSeverity)}
              className="rounded border border-border bg-panel2 px-2 py-2 text-xs text-text outline-none focus:border-accent"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <input
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            placeholder="Wallet address (optional)"
            className="w-full rounded border border-border bg-panel2 px-3 py-2 text-sm text-text outline-none placeholder:text-dim focus:border-accent"
          />
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full resize-none rounded border border-border bg-panel2 px-3 py-2 text-sm text-text outline-none placeholder:text-dim focus:border-accent"
          />
          <button
            type="submit"
            disabled={saving || !title.trim()}
            className="rounded border border-accent/50 bg-accent/10 px-4 py-2 text-xs uppercase tracking-widest text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "adding…" : "add"}
          </button>
        </form>
      </Panel>

      {/* Findings as a chain-of-custody spine — same visual grammar as the
          evidence chain on a wallet page: this case's record IS a chain of
          evidence, accumulated over time. */}
      <Panel title={`Findings (${detail.findings.length})`}>
        {detail.findings.length === 0 ? (
          <p className="text-sm text-muted">
            No findings yet. Add one above, or pin a wallet to this case from
            its investigation page.
          </p>
        ) : (
          <ol className="relative space-y-4 pl-9">
            <span className="absolute left-[13px] top-1 h-[calc(100%-0.5rem)] w-px bg-border" />
            {detail.findings.map((f) => (
              <li key={f.id} className="relative">
                <span className="absolute -left-[30px] top-1 h-2.5 w-2.5 rounded-full border border-accent/60 bg-bg" />
                <div className="flex items-center gap-2">
                  <Pill tone={SEV_TONE[f.severity]}>{f.severity}</Pill>
                  <span className="font-display font-semibold text-text">{f.title}</span>
                  <span className="ml-auto text-[10px] text-dim">{fmtTime(f.created_at)}</span>
                </div>
                {f.wallet_address && (
                  <Link
                    href={`/wallets/${f.wallet_address}`}
                    className="mt-1 inline-block font-mono text-xs text-accent hover:underline"
                  >
                    {shortAddr(f.wallet_address)} ↗
                  </Link>
                )}
                {f.description && (
                  <p className="mt-1 text-[13px] leading-snug text-text">{f.description}</p>
                )}
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </div>
  );
}
