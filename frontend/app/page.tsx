import Link from "next/link";
import { ArrowRight, BadgeCheck, ShieldAlert, Search, Waypoints } from "lucide-react";
import { Eyebrow, Pill, BentoGrid, Tile, Button } from "@/components/ui";
import { DEMO_WALLETS, shortAddr } from "@/lib/format";

const OUTCOME_TONE: Record<string, "good" | "warn" | "accent" | "muted" | "info"> = {
  "clean attribution (Binance)": "good",
  "insufficient evidence": "muted",
  "real: multi-chain": "info",
};

// A deliberately small sample — the clean-attribution win, the honest
// "insufficient evidence" outcome, and the real multi-chain case — so a
// first-time visitor sees the range of outcomes without a wall of cards.
// The full set of 7 lives on /trace.
const HIGHLIGHTS = [0, 2, 6];

const FACTS = [
  { n: "3", l: "chains traced live" },
  { n: "6", l: "evidence signal types" },
  { n: "0", l: "LLMs in the attribution path" },
];

const FLOW = [
  {
    icon: Search,
    title: "Paste a wallet",
    body: "Any real Ethereum, Polygon, or Tron address — fetched live from chain, no manual export needed.",
  },
  {
    icon: Waypoints,
    title: "Traverse the graph",
    body: "A bounded traversal follows the money outward, clustering deposit addresses and known exchange wallets along the way.",
  },
  {
    icon: BadgeCheck,
    title: "Attribute, with evidence",
    body: "A calibrated classifier scores each candidate exchange. Below the confidence threshold, it says “insufficient evidence” instead of guessing.",
  },
  {
    icon: ShieldAlert,
    title: "Score risk, separately",
    body: "Mixer exposure, sanctioned counterparties, and layering patterns are scored independently of attribution confidence.",
  },
];

export default function Home() {
  return (
    <div className="space-y-20">
      {/* ── Hero ── */}
      <div className="mx-auto max-w-3xl text-center">
        <Eyebrow tone="accent" className="text-center">
          Forensic wallet attribution
        </Eyebrow>
        <h1 className="mx-auto mt-4 max-w-2xl font-display text-[36px] font-semibold leading-[1.15] tracking-tight text-heading sm:text-[46px]">
          Trace any wallet to the{" "}
          <span className="text-primary">exchange behind it</span>.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-[16px] leading-relaxed text-body">
          Attribution from on-chain heuristics and a calibrated classifier — every score
          traces to concrete evidence, and the system will say{" "}
          <span className="font-medium text-heading">&ldquo;insufficient evidence&rdquo;</span>{" "}
          rather than guess.
        </p>
        <div className="mt-8 flex justify-center">
          <Link href="/trace">
            <Button variant="primary" className="flex items-center gap-2 !px-7 !py-3.5 text-[14px]">
              Start a trace
              <ArrowRight size={16} />
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Stats ── */}
      <BentoGrid>
        {FACTS.map((f) => (
          <Tile key={f.l} className="col-span-4" bodyClassName="flex items-center gap-4 px-6 py-5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-btn bg-primary-soft">
              <span className="font-display text-xl font-bold text-primary">{f.n}</span>
            </div>
            <span className="text-[14px] leading-tight text-body">{f.l}</span>
          </Tile>
        ))}
      </BentoGrid>

      {/* ── How it works ── */}
      <div>
        <div className="flex items-center gap-3 pb-6">
          <Eyebrow>How it works</Eyebrow>
          <span className="h-px flex-1 bg-soft-border" />
        </div>
        <BentoGrid>
          {FLOW.map((step, i) => (
            <Tile key={step.title} className="col-span-4 md:col-span-3" bodyClassName="p-6">
              <div className="flex h-9 w-9 items-center justify-center rounded-btn bg-primary-soft">
                <step.icon size={17} className="text-primary" />
              </div>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="font-mono text-[11px] text-muted">0{i + 1}</span>
                <span className="font-display text-[15px] font-semibold text-heading">{step.title}</span>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-muted">{step.body}</p>
            </Tile>
          ))}
        </BentoGrid>
      </div>

      {/* ── Demo data, kept deliberately compact — the full set lives on /trace ── */}
      <div>
        <div className="flex items-center gap-3 pb-6">
          <Eyebrow>Example outcomes</Eyebrow>
          <span className="h-px flex-1 bg-soft-border" />
        </div>
        <BentoGrid>
          {HIGHLIGHTS.map((i) => {
            const w = DEMO_WALLETS[i];
            return (
              <Tile key={w.address} interactive className="col-span-4" bodyClassName="p-6">
                <Link href={`/wallets/${w.address}`} className="group flex h-full flex-col">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase text-muted">
                      CASE-{String(i + 1).padStart(2, "0")}
                    </span>
                    <Pill tone={OUTCOME_TONE[w.note] ?? "muted"}>{w.note}</Pill>
                  </div>
                  <div className="mt-4 font-display text-[18px] font-semibold text-heading group-hover:text-primary">
                    {w.label}
                  </div>
                  <div className="mt-2 inline-block w-fit rounded-lg bg-surface-lavender px-2.5 py-1 font-mono text-xs text-mono">
                    {shortAddr(w.address, 10, 8)}
                  </div>
                  <div className="mt-auto pt-4 text-[11px] text-muted opacity-0 transition-opacity group-hover:opacity-100">
                    open investigation →
                  </div>
                </Link>
              </Tile>
            );
          })}
        </BentoGrid>
        <div className="mt-6 flex items-center justify-between">
          <p className="text-xs text-muted">
            Start the API (<code className="rounded-lg bg-surface-lavender px-1.5 py-0.5 font-mono text-mono">uvicorn app.main:app</code>) and
            seed data (<code className="rounded-lg bg-surface-lavender px-1.5 py-0.5 font-mono text-mono">make seed-demo</code>) first.
          </p>
          <Link href="/trace" className="flex shrink-0 items-center gap-1 text-[13px] font-medium text-primary hover:underline">
            View all example cases
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    </div>
  );
}
