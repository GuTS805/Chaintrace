import Link from "next/link";
import { WalletSearch } from "@/components/WalletSearch";
import { Eyebrow, Pill, Kbd, BentoGrid, Tile } from "@/components/ui";
import { DEMO_WALLETS, shortAddr } from "@/lib/format";

const OUTCOME_TONE: Record<string, "good" | "warn" | "accent" | "muted" | "info"> = {
  "clean attribution (Binance)": "good",
  "peel chain → Kraken": "warn",
  "insufficient evidence": "muted",
  "ambiguous split": "accent",
  "real: Kraken deposit": "good",
  "real: Binance deposit": "good",
  "real: multi-chain": "info",
};

// 3 columns: each case is col-span-4, CASE-07 is full-width
const CASE_SPAN = [
  "col-span-4", // CASE-01
  "col-span-4", // CASE-02
  "col-span-4", // CASE-03
  "col-span-4", // CASE-04
  "col-span-4", // CASE-05
  "col-span-4", // CASE-06
  "col-span-4 md:col-span-12", // CASE-07 — full-width
];

export default function TracePage() {
  return (
    <div className="space-y-12">
      <div>
        <Eyebrow tone="accent">Trace a wallet</Eyebrow>
        <h1 className="mt-3 font-display text-[28px] font-semibold tracking-tight text-heading">
          Paste a wallet address to start
        </h1>
        <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-body">
          Works with any real Ethereum, Polygon, or Tron wallet — fetched live from chain — or
          jump into one of the seeded example cases below.
        </p>
        <div className="mt-6 max-w-2xl">
          <WalletSearch autoFocus />
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-xs text-muted">
          or press <Kbd>⌘K</Kbd> to jump anywhere, any time
        </div>
      </div>

      <div>
        <div className="flex items-center gap-3 pb-6">
          <Eyebrow>Example cases · offline seeded</Eyebrow>
          <span className="h-px flex-1 bg-soft-border" />
        </div>

        <BentoGrid>
          {DEMO_WALLETS.map((w, i) => (
            <Tile
              key={w.address}
              interactive
              className={CASE_SPAN[i] ?? "col-span-4"}
              bodyClassName="p-6"
            >
              <Link href={`/wallets/${w.address}`} className="group flex h-full flex-col">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase text-muted">
                    CASE-{String(i + 1).padStart(2, "0")}
                  </span>
                  <Pill tone={OUTCOME_TONE[w.note] ?? "muted"}>{w.note}</Pill>
                </div>
                <div className="mt-4 font-display text-[20px] font-semibold text-heading group-hover:text-primary">
                  {w.label}
                </div>
                <div className="mt-2 inline-block rounded-lg bg-surface-lavender px-2.5 py-1 font-mono text-xs text-mono">
                  {shortAddr(w.address, 10, 8)}
                </div>
                <div className="mt-auto pt-4 text-[11px] text-muted opacity-0 transition-opacity group-hover:opacity-100">
                  open investigation →
                </div>
              </Link>
            </Tile>
          ))}
        </BentoGrid>

        <p className="mt-8 text-xs text-muted">
          Start the API (<code className="rounded-lg bg-surface-lavender px-1.5 py-0.5 font-mono text-mono">uvicorn app.main:app</code>) and
          seed data (<code className="rounded-lg bg-surface-lavender px-1.5 py-0.5 font-mono text-mono">make seed-demo</code>) first. Manage
          investigations under{" "}
          <Link href="/cases" className="font-medium text-primary hover:underline">
            cases
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
