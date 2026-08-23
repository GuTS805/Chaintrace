"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { LiveTraceResult } from "@/lib/types";
import { Panel, Pill } from "./ui";

type Status = "idle" | "loading" | "error" | "done";

export function LiveTrace({
  address,
  onDone,
}: {
  address: string;
  onDone: () => void;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<LiveTraceResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runTrace() {
    setStatus("loading");
    setError(null);
    try {
      const data = await api.liveTrace(address);
      setResult(data);
      setStatus("done");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live trace failed.");
      setStatus("error");
    }
  }

  return (
    <Panel title="Live trace">
      <p className="mb-3 text-xs text-muted">
        This wallet isn&apos;t in the local store. Pull its transactions live from
        Ethereum (via Blockscout) and run the same pipeline on it.
      </p>

      {status === "idle" && (
        <button
          onClick={runTrace}
          className="rounded-md border border-accent/50 bg-accent/10 px-4 py-2 text-accent hover:bg-accent/20"
        >
          ⚡ Fetch from Ethereum (live)
        </button>
      )}

      {status === "loading" && (
        <div className="flex items-center gap-2 text-muted motion-safe:animate-pulse">
          <span className="h-2 w-2 rounded-full bg-accent" />
          Querying Ethereum via Blockscout…
        </div>
      )}

      {status === "error" && (
        <div className="flex flex-col gap-2">
          <p className="text-bad">{error ?? "Something went wrong."}</p>
          <button
            onClick={runTrace}
            className="self-start rounded border border-border px-3 py-1.5 text-xs text-muted hover:text-accent"
          >
            retry
          </button>
        </div>
      )}

      {status === "done" && result && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-good">
            imported {result.imported_transactions} txs
          </span>
          <Pill tone="muted">
            {result.source === "cache" ? "from cache" : "from Blockscout"}
          </Pill>
        </div>
      )}
    </Panel>
  );
}
