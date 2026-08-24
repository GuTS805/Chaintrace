"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { EvmChain, LiveTraceResult } from "@/lib/types";
import { Panel, Pill } from "./ui";

type Status = "idle" | "loading" | "error" | "done";

// EVM address format is chain-agnostic (0x… looks the same on every EVM
// chain), so unlike Tron this can't be auto-detected — the investigator has
// to say which chain the address was reported on.
const EVM_CHAIN_LABEL: Record<EvmChain, string> = {
  ethereum: "Ethereum",
  polygon: "Polygon",
};
const isEvmAddress = (address: string) => address.startsWith("0x");

export function LiveTrace({
  address,
  onDone,
}: {
  address: string;
  onDone: (chain: string) => void;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<LiveTraceResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chain, setChain] = useState<EvmChain>("ethereum");

  async function runTrace() {
    setStatus("loading");
    setError(null);
    try {
      const data = await api.liveTrace(address, chain);
      setResult(data);
      setStatus("done");
      onDone(data.chain);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live trace failed.");
      setStatus("error");
    }
  }

  return (
    <Panel title="Live trace">
      <p className="mb-3 text-xs text-muted">
        This wallet isn&apos;t in the local store. Pull its transactions live
        from the chain (via Blockscout / TronGrid) and run the same pipeline
        on it.
      </p>

      {status === "idle" && isEvmAddress(address) && (
        <div className="mb-3 flex flex-wrap gap-2">
          {(Object.keys(EVM_CHAIN_LABEL) as EvmChain[]).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setChain(c)}
              className={`rounded border px-2.5 py-1 text-[11px] transition-colors ${
                chain === c
                  ? "border-accent/50 bg-accent/10 text-accent"
                  : "border-border text-muted hover:border-accent/40 hover:text-accent"
              }`}
            >
              {EVM_CHAIN_LABEL[c]}
            </button>
          ))}
        </div>
      )}

      {status === "idle" && (
        <button
          onClick={runTrace}
          className="rounded-md border border-accent/50 bg-accent/10 px-4 py-2 text-accent hover:bg-accent/20"
        >
          ⚡ Fetch from {isEvmAddress(address) ? EVM_CHAIN_LABEL[chain] : "Tron"} (live)
        </button>
      )}

      {status === "loading" && (
        <div className="flex items-center gap-2 text-muted motion-safe:animate-pulse">
          <span className="h-2 w-2 rounded-full bg-accent" />
          Querying {isEvmAddress(address) ? EVM_CHAIN_LABEL[chain] : "Tron"}…
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
