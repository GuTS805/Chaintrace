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

const FACTS = [
  { n: "3", l: "chains traced live" },
  { n: "6", l: "evidence signal types" },
  { n: "0", l: "LLMs in the attribution path" },
];

export default function Home() {
  return (
    <div className="space-y-16">
      {/* ── Hero + Stats row ── */}
      <BentoGrid>
        {/* Hero panel (~66%) */}
        <Tile className="col-span-4 md:col-span-8" bodyClassName="p-8">
          <Eyebrow tone="accent">Forensic wallet attribution</Eyebrow>
          <h1 className="mt-4 font-display text-[34px] font-semibold leading-[1.15] tracking-tight text-heading sm:text-[42px]">
            Trace any wallet to the{" "}
            <span className="text-primary">exchange behind it</span>.
          </h1>
          <p className="mt-5 max-w-2xl text-[16px] leading-relaxed text-body">
            Attribution from on-chain heuristics and a calibrated classifier — every
            score traces to concrete evidence, and the system will say{" "}
            <span className="font-medium text-heading">&ldquo;insufficient evidence&rdquo;</span>{" "}
            rather than guess.
          </p>
          <div className="mt-6">
            <WalletSearch autoFocus />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted">
            <span>
              Paste <span className="font-medium text-primary">any real wallet</span> (Ethereum,
              Polygon, or Tron) and fetch it live from chain.
            </span>
            <span className="flex items-center gap-1.5">
              or press <Kbd>⌘K</Kbd> to jump anywhere
            </span>
          </div>
        </Tile>

        {/* Stats sidebar (~34%) — three stacked tiles */}
        <div className="col-span-4 flex flex-col gap-4 md:col-span-4">
          {FACTS.map((f) => (
            <Tile key={f.l} bodyClassName="flex items-center gap-4 px-6 py-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-btn bg-primary-soft">
                <span className="font-display text-xl font-bold text-primary">{f.n}</span>
              </div>
              <span className="text-[14px] leading-tight text-body">{f.l}</span>
            </Tile>
          ))}
        </div>
      </BentoGrid>

      {/* ── Case files ── */}
      <div>
        <div className="flex items-center gap-3 pb-6">
          <Eyebrow>Case files · offline seeded</Eyebrow>
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
