"use client";

import { useEffect, useState } from "react";
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
  const [selected, setSelected] = useState<string>("");
  const [note, setNote] = useState("");
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

  const top = attribution?.candidates[0];
  const defaultSummary = top
    ? `Attributed to ${top.vasp_name} (${pct(top.probability, 1)})`
    : "No confident attribution.";

  async function attach() {
    if (!selected) return;
    setStatus("Pinning…");
    try {
      await api.addFinding(Number(selected), {
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
        <p className="text-[13px] text-muted">No cases yet. Create one under “cases”.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="flex-1 rounded-md border border-border bg-panel2 px-2.5 py-2 text-[13px] outline-none focus:border-accent"
            >
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.id} · {c.name}
                </option>
              ))}
            </select>
            <Button variant="primary" onClick={attach}>
              Pin
            </Button>
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={`Why does this matter? (default: "${defaultSummary}")`}
            rows={2}
            className="w-full resize-none rounded-md border border-border bg-panel2 px-2.5 py-2 text-[13px] text-text outline-none placeholder:text-dim focus:border-accent"
          />
        </div>
      )}
      {status && <p className="mt-2 text-[12px] text-muted">{status}</p>}
    </Tile>
  );
}
