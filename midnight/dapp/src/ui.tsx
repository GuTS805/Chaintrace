// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { type ReactNode, useState } from "react";
import type { TxStage } from "../../src/tx-stages.js";

export function FileDrop({
  label,
  accept = "application/json,.json",
  onText,
}: {
  label: string;
  accept?: string;
  onText: (text: string, name: string) => void;
}) {
  const [over, setOver] = useState(false);
  const read = (file: File | undefined) => {
    if (file) void file.text().then((t) => onText(t, file.name));
  };
  return (
    <label
      className={`drop${over ? " over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        read(e.dataTransfer.files[0]);
      }}
    >
      <input type="file" accept={accept} onChange={(e) => read(e.target.files?.[0])} />
      {label}
      <span className="note">Read in this browser only. Nothing is uploaded.</span>
    </label>
  );
}

export function KV({ items }: { items: Array<[string, ReactNode]> }) {
  return (
    <dl className="kv">
      {items.map(([k, v]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

const ORDER = ["proving", "balancing", "prepared", "submitted", "confirmed"] as const;
const LABELS: Record<(typeof ORDER)[number], string> = {
  proving: "Generate zero-knowledge proof (local proof server)",
  balancing: "Wallet balances fees and signs",
  prepared: "Prepared: proven and signed",
  submitted: "Submitted to Midnight",
  confirmed: "Confirmed: included in a block and ledger re-read",
};

export function StageTracker({ title, stage }: { title: string; stage: TxStage }) {
  const failed = stage.stage === "failed";
  const index = ORDER.indexOf(stage.stage as (typeof ORDER)[number]);
  return (
    <div className="stack" style={{ gap: 8 }}>
      <h3>{title}</h3>
      <ol className="steps" aria-live="polite">
        {ORDER.map((s, i) => {
          const state =
            stage.stage === "confirmed" || i < index ? "done" : i === index ? (failed ? "failed" : "active") : "";
          return (
            <li key={s} className={`step ${state}`}>
              <span className="dot" aria-hidden />
              {LABELS[s]}
              {s === "submitted" && "txId" in stage && i <= index && <span className="mono">{short(stage.txId)}</span>}
            </li>
          );
        })}
      </ol>
      {failed && <p className="alert bad">{stage.error}</p>}
    </div>
  );
}

export function short(hex: string, n = 10): string {
  return hex.length > n * 2 + 1 ? `${hex.slice(0, n)}…${hex.slice(-n)}` : hex;
}

export function download(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, (_, v) => (typeof v === "bigint" ? v.toString() : v), 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function errorText(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  return msg.length > 400 ? `${msg.slice(0, 400)}…` : msg;
}
