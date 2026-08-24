"use client";

import { Fragment, useEffect, useState } from "react";
import { Listbox, Transition } from "@headlessui/react";
import { ChevronsUpDown, Pin } from "lucide-react";
import { api } from "@/lib/api";
import type { AttributionResult, CaseOut } from "@/lib/types";
import { pct, shortAddr } from "@/lib/format";
import { Button, Tile } from "./ui";

export function AddToCase({
  address,
  attribution,
}: {
  address: string;
  attribution: AttributionResult | null;
}) {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [selected, setSelected] = useState<CaseOut | null>(null);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    api
      .listCases()
      .then((cs) => {
        setCases(cs);
        if (cs.length > 0) setSelected(cs[0]);
      })
      .catch(() => setStatus("Could not load cases."));
  }, []);

  const top = attribution?.candidates[0];
  const defaultSummary = top
    ? `Attributed to ${top.vasp_name} (${pct(top.probability, 1)})`
    : "No confident attribution.";

  async function attach() {
    if (!selected) return;
    setStatus("Pinning…");
    try {
      await api.addFinding(selected.id, {
        title: `Wallet ${shortAddr(address)}`,
        wallet_address: address,
        severity: attribution?.insufficient_evidence ? "INFO" : "MEDIUM",
        description: note.trim() || defaultSummary,
        evidence: attribution ? { model_version: attribution.model_version } : undefined,
      });
      setStatus("Pinned to case.");
      setNote("");
    } catch {
      setStatus("Failed to pin.");
    }
  }

  return (
    <Tile title="Pin to case">
      {cases.length === 0 ? (
        <p className="text-[13px] text-muted">No cases yet. Create one under &ldquo;cases&rdquo;.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Listbox value={selected} onChange={setSelected}>
              <div className="relative flex-1">
                <Listbox.Button className="flex w-full items-center justify-between rounded-input border border-soft-border bg-surface-lavender px-3 py-2.5 text-left text-[13px] text-heading outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft">
                  <span className="truncate">
                    {selected ? `#${selected.id} · ${selected.name}` : "Select a case"}
                  </span>
                  <ChevronsUpDown size={14} className="shrink-0 text-muted" />
                </Listbox.Button>
                <Transition
                  as={Fragment}
                  leave="transition ease-in duration-100"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <Listbox.Options className="absolute z-10 mt-1.5 max-h-56 w-full overflow-auto rounded-card bg-white p-1.5 text-[13px] shadow-card-hover focus:outline-none">
                    {cases.map((c) => (
                      <Listbox.Option
                        key={c.id}
                        value={c}
                        className={({ active }) =>
                          `cursor-pointer select-none truncate rounded-btn px-3 py-2 ${
                            active ? "bg-surface-lavender text-heading" : "text-body"
                          }`
                        }
                      >
                        #{c.id} · {c.name}
                      </Listbox.Option>
                    ))}
                  </Listbox.Options>
                </Transition>
              </div>
            </Listbox>
            <Button variant="primary" onClick={attach} className="flex shrink-0 items-center gap-1.5">
              <Pin size={13} />
              Pin
            </Button>
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={`Why does this matter? (default: "${defaultSummary}")`}
            rows={2}
            className="w-full resize-none rounded-input border border-soft-border bg-surface-lavender px-3 py-2.5 text-[13px] text-heading outline-none placeholder:text-muted transition-all focus:border-primary focus:ring-2 focus:ring-primary-soft"
          />
        </div>
      )}
      {status && <p className="mt-2 text-[12px] text-muted">{status}</p>}
    </Tile>
  );
}
