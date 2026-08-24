import Link from "next/link";
import { WalletSearch } from "@/components/WalletSearch";
import { Eyebrow, Pill, Kbd, BentoGrid, Tile } from "@/components/ui";
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

// Deliberately variable spans — the case that best demonstrates the product
// (a clean, evidenced attribution) gets the biggest tile; the honest
// "insufficient evidence" case earns its own visual weight too, since that
// answer is as much the point as a confident one. Sized by narrative
// importance, not just alphabetically or by index.
const CASE_SPAN = [
  "col-span-4 md:col-span-6", // ransomware -> Binance (headline case)
  "col-span-2 md:col-span-3", // peel chain
  "col-span-2 md:col-span-3", // insufficient evidence
  "col-span-4 md:col-span-4", // ambiguous split
  "col-span-2 md:col-span-4", // real Kraken
  "col-span-2 md:col-span-4", // real Binance
  "col-span-4 md:col-span-12", // real Tron — the multi-chain banner
];

const FACTS = [
  { n: "3", l: "chains traced live" },
  { n: "6", l: "evidence signal types" },
  { n: "0", l: "LLMs in the attribution path" },
];

export default function Home() {
  return (
    <BentoGrid>
      <Tile className="col-span-4 md:col-span-8" bodyClassName="p-8 sm:p-10">
        <Eyebrow tone="accent">Forensic wallet attribution</Eyebrow>
        <h1 className="mt-4 font-display text-[34px] font-semibold leading-[1.1] tracking-tight text-text sm:text-[42px]">
          Trace any wallet to the{" "}
          <span className="text-accent">exchange behind it</span>.
        </h1>
        <p className="mt-5 max-w-2xl text-[14px] leading-relaxed text-muted">
          Attribution from on-chain heuristics and a calibrated classifier — every
          score traces to concrete evidence, and the system will say{" "}
          <span className="text-text">&ldquo;insufficient evidence&rdquo;</span>{" "}
          rather than guess.
        </p>
        <div className="mt-6">
          <WalletSearch autoFocus />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted">
          <span>
            Paste <span className="text-accent">any real wallet</span> (Ethereum,
            Polygon, or Tron) and fetch it live from chain.
          </span>
          <span className="flex items-center gap-1.5">
            or press <Kbd>⌘K</Kbd> to jump anywhere
          </span>
        </div>
      </Tile>

      <Tile className="col-span-4 md:col-span-4" bodyClassName="flex flex-col divide-y divide-border p-0">
        {FACTS.map((f) => (
          <div key={f.l} className="flex flex-1 items-center gap-4 px-5 py-3">
            <span className="font-display text-3xl font-bold tabular-nums text-accent">
              {f.n}
            </span>
            <span className="text-xs leading-tight text-muted">{f.l}</span>
          </div>
        ))}
      </Tile>

      <div className="col-span-4 flex items-center gap-3 pb-1 pt-4 md:col-span-12">
        <Eyebrow>Case files · offline seeded</Eyebrow>
        <span className="h-px flex-1 bg-border" />
      </div>

      {DEMO_WALLETS.map((w, i) => (
        <Tile
          key={w.address}
          interactive
          className={CASE_SPAN[i] ?? "col-span-4"}
          bodyClassName="p-4"
        >
          <Link href={`/wallets/${w.address}`} className="group flex h-full flex-col">
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
            <div className="mt-auto pt-3 text-[11px] text-dim opacity-0 transition-opacity group-hover:opacity-100">
              open investigation →
            </div>
          </Link>
        </Tile>
      ))}

      <div className="col-span-4 md:col-span-12">
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
    </BentoGrid>
  );
}
