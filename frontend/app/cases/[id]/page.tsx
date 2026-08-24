"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Listbox, Transition } from "@headlessui/react";
import { ArrowLeft, ChevronsUpDown, Download, ExternalLink, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { CaseDetail, CaseStatus, FindingSeverity } from "@/lib/types";
import { PdfButton } from "@/components/PdfButton";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { BentoGrid, Button, Tile, Pill } from "@/components/ui";
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
  const [confirmDelete, setConfirmDelete] = useState(false);

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
    await api.deleteCase(caseId);
    router.push("/cases");
  }

  if (error) return <p className="text-sm text-bad-text">{error}</p>;
  if (!detail) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <BentoGrid>
      <div className="col-span-4 md:col-span-12">
        <Link href="/cases" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
          <ArrowLeft size={13} />
          cases
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className="font-mono text-xs text-muted">{caseRef(detail.id)}</span>
          <h1 className="font-display text-[26px] font-bold tracking-tight text-heading">{detail.name}</h1>
          <Pill tone={STATUS_TONE[detail.status]}>{detail.status}</Pill>
          <PdfButton
            path={`/cases/${caseId}/report`}
            className="ml-auto flex items-center gap-1.5 rounded-btn border border-soft-border px-3 py-1.5 text-xs text-muted transition-all hover:bg-surface-lavender hover:text-heading"
          >
            <Download size={13} />
            Report (PDF)
          </PdfButton>
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-1.5 rounded-btn bg-bad-fill px-3 py-1.5 text-xs font-medium text-bad-text transition-all hover:bg-bad-fill/80"
          >
            <Trash2 size={13} />
            Delete
          </button>
        </div>
        {detail.investigator && (
          <p className="mt-1 text-xs text-muted">investigator: {detail.investigator}</p>
        )}
      </div>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this case?"
        description={`${caseRef(detail.id)} · ${detail.name} and all its findings will be permanently removed. This cannot be undone.`}
        confirmLabel="Delete case"
        onConfirm={remove}
      />

      <Tile title="Add finding / note" className="col-span-4 md:col-span-5" bodyClassName="p-6">
        <form onSubmit={addFinding} className="space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What did you find?"
            className="w-full rounded-input border border-soft-border bg-surface-lavender px-3 py-2.5 text-sm text-heading outline-none placeholder:text-muted transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
          <Listbox value={severity} onChange={setSeverity}>
            <div className="relative">
              <Listbox.Button className="flex w-full items-center justify-between rounded-input border border-soft-border bg-surface-lavender px-3 py-2.5 text-left text-xs text-heading outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft">
                <span className="flex items-center gap-2">
                  <Pill tone={SEV_TONE[severity]}>{severity}</Pill>
                </span>
                <ChevronsUpDown size={14} className="shrink-0 text-muted" />
              </Listbox.Button>
              <Transition
                as={Fragment}
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <Listbox.Options className="absolute z-10 mt-1.5 w-full overflow-auto rounded-card border border-soft-border bg-surface p-1.5 shadow-card-hover focus:outline-none">
                  {SEVERITIES.map((s) => (
                    <Listbox.Option
                      key={s}
                      value={s}
                      className={({ active }) =>
                        `flex cursor-pointer select-none items-center rounded-btn px-3 py-2 text-xs ${
                          active ? "bg-surface-lavender" : ""
                        }`
                      }
                    >
                      <Pill tone={SEV_TONE[s]}>{s}</Pill>
                    </Listbox.Option>
                  ))}
                </Listbox.Options>
              </Transition>
            </div>
          </Listbox>
          <input
            value={wallet}
            onChange={(e) => setWallet(e.target.value)}
            placeholder="Wallet address (optional)"
            className="w-full rounded-input border border-soft-border bg-surface-lavender px-3 py-2.5 text-sm text-heading outline-none placeholder:text-muted transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full resize-none rounded-input border border-soft-border bg-surface-lavender px-3 py-2.5 text-sm text-heading outline-none placeholder:text-muted transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
          <Button type="submit" variant="primary" disabled={saving || !title.trim()} className="w-full">
            {saving ? "Adding…" : "Add"}
          </Button>
        </form>
      </Tile>

      {/* Findings as a chain-of-custody spine — same visual grammar as the
          evidence chain on a wallet page: this case's record IS a chain of
          evidence, accumulated over time. */}
      <Tile title={`Findings (${detail.findings.length})`} className="col-span-4 md:col-span-7" bodyClassName="p-6">
        {detail.findings.length === 0 ? (
          <p className="text-sm text-muted">
            No findings yet. Add one above, or pin a wallet to this case from
            its investigation page.
          </p>
        ) : (
          <ol className="relative space-y-4 pl-9">
            <span className="absolute left-[13px] top-1 h-[calc(100%-0.5rem)] w-px bg-soft-border" />
            {detail.findings.map((f) => (
              <li key={f.id} className="relative">
                <span className="absolute -left-[30px] top-1 h-2.5 w-2.5 rounded-full border-2 border-primary bg-surface" />
                <div className="flex items-center gap-2">
                  <Pill tone={SEV_TONE[f.severity]}>{f.severity}</Pill>
                  <span className="font-display font-semibold text-heading">{f.title}</span>
                  <span className="ml-auto text-[10px] text-muted">{fmtTime(f.created_at)}</span>
                </div>
                {f.wallet_address && (
                  <Link
                    href={`/wallets/${f.wallet_address}`}
                    className="mt-1 inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline"
                  >
                    {shortAddr(f.wallet_address)}
                    <ExternalLink size={11} />
                  </Link>
                )}
                {f.description && (
                  <p className="mt-1 text-[13px] leading-snug text-body">{f.description}</p>
                )}
              </li>
            ))}
          </ol>
        )}
      </Tile>
    </BentoGrid>
  );
}
