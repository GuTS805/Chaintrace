import Link from "next/link";
import { WalletSearch } from "@/components/WalletSearch";
import { Pill, Kbd } from "@/components/ui";
import { DEMO_WALLETS, shortAddr } from "@/lib/format";

const OUTCOME_TONE: Record<string, "good" | "warn" | "accent" | "muted" | "gold"> = {
  "clean attribution (Binance)": "good",
  "peel chain → Kraken": "warn",
  "insufficient evidence": "muted",
  "ambiguous split": "accent",
  "real: Kraken deposit": "good",
  "real: Binance deposit": "good",
  "real: multi-chain": "gold",
};

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl space-y-10 pt-6">
      <section className="space-y-5">
        <div className="text-[11px] uppercase tracking-widest text-accent">
          forensic wallet attribution
        </div>
        <h1 className="font-display text-4xl font-bold leading-[1.1] text-text sm:text-5xl">
          Trace any wallet to the{" "}
          <span className="text-accent">exchange behind it</span>.
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted">
          Attribution from on-chain heuristics and a calibrated classifier — every
          score traces to concrete evidence, and the system will say{" "}
          <span className="text-text">&ldquo;insufficient evidence&rdquo;</span>{" "}
          rather than guess. No LLM in the attribution path.
        </p>
        <WalletSearch autoFocus />
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
          <span>
            Paste <span className="text-accent">any real wallet</span> (Ethereum or
            Tron) and fetch it live from chain.
          </span>
          <span className="flex items-center gap-1.5">
            or press <Kbd>⌘K</Kbd> to jump anywhere
          </span>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-widest text-muted">
            case files · offline seeded
          </span>
          <span className="h-px flex-1 bg-border" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {DEMO_WALLETS.map((w, i) => (
            <Link
              key={w.address}
              href={`/wallets/${w.address}`}
              className="group rounded-lg border border-border bg-panel p-4 transition-colors hover:border-accent/50 hover:bg-panel2"
            >
              <div className="flex items-center justify-between">
                <span className="font-display text-[10px] tabular-nums text-dim">
                  CASE-{String(i + 1).padStart(2, "0")}
                </span>
                <Pill tone={OUTCOME_TONE[w.note] ?? "muted"}>{w.note}</Pill>
              </div>
              <div className="mt-2 font-display text-base font-semibold text-text group-hover:text-accent">
                {w.label}
              </div>
              <div className="mt-1 font-mono text-xs text-muted">
                {shortAddr(w.address, 10, 8)}
              </div>
            </Link>
          ))}
        </div>
      </section>

      <p className="text-xs text-muted">
        Start the API (<code className="text-text">uvicorn app.main:app</code>) and
        seed data (<code className="text-text">make seed-demo</code>) first. Manage
        investigations under{" "}
        <Link href="/cases" className="text-accent hover:underline">
          cases
        </Link>
        .
      </p>
    </div>
  );
}
