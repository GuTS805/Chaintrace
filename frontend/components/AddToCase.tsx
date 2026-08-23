"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AttributionResult, CaseOut } from "@/lib/types";
import { pct, shortAddr } from "@/lib/format";
import { Panel } from "./ui";

export function AddToCase({
  address,
  attribution,
}: {
  address: string;
  attribution: AttributionResult | null;
}) {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    api
      .listCases()
      .then((cs) => {
        setCases(cs);
        if (cs.length > 0) setSelected(String(cs[0].id));
      })
      .catch(() => setStatus("Could not load cases."));
  }, []);

  async function attach() {
    if (!selected) return;
    setStatus("Saving…");
    const top = attribution?.candidates[0];
    try {
      await api.addFinding(Number(selected), {
        title: `Wallet ${shortAddr(address)}`,
        wallet_address: address,
        severity: attribution?.insufficient_evidence ? "INFO" : "MEDIUM",
        description: top
          ? `Attributed to ${top.vasp_name} (${pct(top.probability, 1)})`
          : "No confident attribution.",
        evidence: attribution ? { model_version: attribution.model_version } : undefined,
      });
      setStatus("Attached to case.");
    } catch {
      setStatus("Failed to attach.");
    }
  }

  return (
    <Panel title="Case">
      {cases.length === 0 ? (
        <p className="text-xs text-muted">
          No cases yet. Create one under “cases”.
        </p>
      ) : (
        <div className="flex items-center gap-2">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="flex-1 rounded border border-border bg-panel2 px-2 py-1.5 text-xs outline-none focus:border-accent"
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} · {c.name}
              </option>
            ))}
          </select>
          <button
            onClick={attach}
            className="rounded border border-accent/50 bg-accent/10 px-3 py-1.5 text-xs text-accent hover:bg-accent/20"
          >
            attach
          </button>
        </div>
      )}
      {status && <p className="mt-2 text-[11px] text-muted">{status}</p>}
    </Panel>
  );
}
