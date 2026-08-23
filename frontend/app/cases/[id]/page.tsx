"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CaseDetail, FindingSeverity } from "@/lib/types";
import { Panel, Pill } from "@/components/ui";
import { fmtTime, shortAddr } from "@/lib/format";

const SEVERITIES: FindingSeverity[] = [
  "INFO",
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

const SEV_TONE: Record<string, "muted" | "warn" | "bad"> = {
  INFO: "muted",
  LOW: "muted",
  MEDIUM: "warn",
  HIGH: "bad",
  CRITICAL: "bad",
};

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
    }
  }

  async function remove() {
    if (!confirm("Delete this case?")) return;
    await api.deleteCase(caseId);
    router.push("/cases");
  }

  if (error) return <p className="text-sm text-bad">{error}</p>;
  if (!detail) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/cases" className="text-xs text-muted hover:text-text">
          ← cases
        </Link>
        <h1 className="text-base font-semibold">{detail.name}</h1>
        <Pill tone="accent">{detail.status}</Pill>
        <button
          onClick={remove}
          className="ml-auto rounded border border-bad/40 px-2 py-1 text-xs text-bad hover:bg-bad/10"
        >
          delete
        </button>
      </div>
      {detail.investigator && (
        <p className="text-xs text-muted">investigator: {detail.investigator}</p>
      )}

      <Panel title="Add finding / note">
        <form onSubmit={addFinding} className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Finding title"
              className="min-w-[220px] flex-1 rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
            />
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as FindingSeverity)}
              className="rounded border border-border bg-panel2 px-2 py-2 text-xs outline-none focus:border-accent"
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
            className="w-full rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
          />
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full rounded border border-border bg-panel2 px-3 py-2 outline-none focus:border-accent"
          />
          <button
            type="submit"
            className="rounded border border-accent/50 bg-accent/10 px-4 py-2 text-accent hover:bg-accent/20"
          >
            add
          </button>
        </form>
      </Panel>

      <Panel title={`Findings (${detail.findings.length})`}>
        {detail.findings.length === 0 ? (
          <p className="text-sm text-muted">No findings yet.</p>
        ) : (
          <ul className="space-y-2">
            {detail.findings.map((f) => (
              <li
                key={f.id}
                className="rounded border border-border bg-panel2 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <Pill tone={SEV_TONE[f.severity] ?? "muted"}>
                    {f.severity}
                  </Pill>
                  <span className="font-semibold text-text">{f.title}</span>
                  <span className="ml-auto text-[10px] text-muted">
                    {fmtTime(f.created_at)}
                  </span>
                </div>
                {f.wallet_address && (
                  <Link
                    href={`/wallets/${f.wallet_address}`}
                    className="mt-1 inline-block text-xs text-accent hover:underline"
                  >
                    {shortAddr(f.wallet_address)}
                  </Link>
                )}
                {f.description && (
                  <p className="mt-1 text-xs text-text">{f.description}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
