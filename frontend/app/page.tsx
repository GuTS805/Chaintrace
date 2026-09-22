"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Database,
  FlaskConical,
  Link2,
  Radio,
  BarChart3,
  Zap,
  BadgeCheck,
  CheckCircle2,
  Clock3,
  Coins,
  FileText,
  Fingerprint,
  Gauge,
  GitBranch,
  HelpCircle,
  Landmark,
  Network,
  Route,
  Scale,
  Search,
  ShieldAlert,
  ShieldCheck,
  Shuffle,
  Sparkles,
  Tags,
  Waypoints,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AttributionResult, GraphResult, RiskResult } from "@/lib/types";
import { DEMO_WALLETS, SIGNAL_LABEL, pct, shortAddr } from "@/lib/format";
import { WalletSearch } from "@/components/WalletSearch";
import { ReferenceGraph } from "@/components/ReferenceGraph";
import { GraphView } from "@/components/GraphView";
import { Eyebrow, Pill, Button, BentoGrid, Tile } from "@/components/ui";

/* ── Scroll-reveal wrapper — subtle, not decorative-for-its-own-sake. ── */
function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function SectionHead({
  eyebrow,
  title,
  sub,
}: {
  eyebrow: string;
  title: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <Eyebrow tone="accent" className="justify-center text-center">
        {eyebrow}
      </Eyebrow>
      <h2 className="mx-auto mt-3 font-display text-[28px] font-semibold leading-[1.2] tracking-tight text-heading sm:text-[34px]">
        {title}
      </h2>
      {sub && <p className="mx-auto mt-3 max-w-xl text-[14px] leading-relaxed text-body">{sub}</p>}
    </div>
  );
}

/* ── Verified numbers only — every figure here is derived from the actual
   codebase (backend/tests, evidence signal set, label datasets), never a
   placeholder marketing number. ── */
const STATS = [
  { n: "2", l: "Supported chains", sub: "Ethereum, Tron" },
  { n: "6", l: "Attribution signals", sub: "independent evidence types" },
  { n: "3", l: "Attribution outcomes", sub: "attributed, ambiguous, insufficient" },
  { n: "150+", l: "Backend tests", sub: "Backend verification suite" },
  { n: "4", l: "Label & sanctions datasets", sub: "Etherscan tags, OFAC SDN, and more" },
];

const HOW = [
  { icon: Search, step: "01", title: "Trace", body: "Follow on-chain activity across supported networks and build a bounded transaction graph." },
  { icon: Network, step: "02", title: "Cluster", body: "Identify connected wallets, deposit addresses, sweep patterns, and known VASP clusters." },
  { icon: BadgeCheck, step: "03", title: "Attribute", body: "Combine six independent signals into a calibrated attribution with explainable evidence." },
  { icon: ShieldAlert, step: "04", title: "Assess", body: "Calculate risk independently using transaction behaviour, typologies, and suspicious counterparties." },
];

const PIPELINE = [
  { icon: Fingerprint, label: "Wallet address" },
  { icon: Route, label: "On-chain activity" },
  { icon: Waypoints, label: "Bounded graph traversal" },
  { icon: Network, label: "VASP cluster" },
  { icon: GitBranch, label: "6-signal attribution" },
  { icon: Gauge, label: "Calibrated confidence" },
  { icon: ShieldAlert, label: "Risk analysis" },
  { icon: FileText, label: "Forensic report" },
];

const SIGNALS: { key: keyof typeof SIGNAL_LABEL; icon: typeof Route; body: string }[] = [
  { key: "HOP_PATH", icon: Route, body: "Traces the transaction path toward known entities and deposit clusters, hop by hop." },
  { key: "DEPOSIT_SWEEP", icon: Coins, body: "Flags consolidation behaviour — many addresses sweeping funds into one exchange hot wallet." },
  { key: "COUNTERPARTY_OVERLAP", icon: Network, body: "Compares the wallet's counterparties against wallets already tied to a known VASP cluster." },
  { key: "TEMPORAL_CORRELATION", icon: Clock3, body: "Measures how closely a deposit's timing lines up with a known exchange's sweep schedule." },
  { key: "KNOWN_LABEL", icon: Tags, body: "Uses verified blockchain-intelligence labels as direct, high-weight attribution evidence." },
  { key: "PATTERN_SIMILARITY", icon: Fingerprint, body: "Compares the observed consolidation pattern against known exchange-deposit fingerprints." },
];

const CHAINS = [
  { name: "Ethereum", assets: ["ETH", "ERC-20"], icon: Waypoints },
  { name: "Tron", assets: ["TRX", "USDT-TRC20"], icon: Network },
];

const SAHYOG_FIELDS = [
  "Full KYC records",
  "Account statement / transaction ledger",
  "Linked bank, UPI, or card details",
  "Login & device (IP) logs",
  "Beneficial ownership, where applicable",
  "Balance & freeze-pending-process status",
];

const TRANSPARENCY = [
  { title: "Supported chains", body: "Currently Ethereum and Tron. Additional chains are added only once ingestion and evidence signals are verified against them." },
  { title: "SAHYOG", body: "ChainTrace drafts a structured disclosure request. It does not submit to the SAHYOG portal directly — filing remains with an authorized officer." },
  { title: "Traversal", body: "Graph exploration uses a bounded, depth- and node-limited traversal, so every investigation stays explainable and reproducible." },
  { title: "Model", body: "Attribution calibration is trained on the project's available synthetic + seeded real-wallet distribution, and is versioned in every result." },
];

const OUTCOME_WALLETS = {
  attributed: DEMO_WALLETS[0], // Ransomware → exchange (clean Binance attribution)
  ambiguous: DEMO_WALLETS[3], // Two exchanges
  insufficient: DEMO_WALLETS[2], // No VASP linkage
};

function chainOf(address: string): "Tron" | "Ethereum" {
  return address.startsWith("T") ? "Tron" : "Ethereum";
}

export default function Home() {
  const router = useRouter();

  const [attributed, setAttributed] = useState<AttributionResult | null>(null);
  const [ambiguous, setAmbiguous] = useState<AttributionResult | null>(null);
  const [insufficient, setInsufficient] = useState<AttributionResult | null>(null);
  const [showcaseGraph, setShowcaseGraph] = useState<GraphResult | null>(null);
  const [showcaseRisk, setShowcaseRisk] = useState<RiskResult | null>(null);
  const [liveDataFailed, setLiveDataFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      api.attribution(OUTCOME_WALLETS.attributed.address).then((r) => !cancelled && setAttributed(r)),
      api.attribution(OUTCOME_WALLETS.ambiguous.address).then((r) => !cancelled && setAmbiguous(r)),
      api.attribution(OUTCOME_WALLETS.insufficient.address).then((r) => !cancelled && setInsufficient(r)),
      api.graph(OUTCOME_WALLETS.attributed.address, 5).then((r) => !cancelled && setShowcaseGraph(r)),
      api.risk(OUTCOME_WALLETS.attributed.address).then((r) => !cancelled && setShowcaseRisk(r)),
    ]).then((results) => {
      if (!cancelled && results.every((r) => r.status === "rejected")) setLiveDataFailed(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const showcaseEvidence = attributed?.candidates[0]?.evidence.find((e) => e.signal_type === "DEPOSIT_SWEEP");
  const riskAddresses = new Set(showcaseRisk?.indicators.map((i) => i.address) ?? []);

  return (
    <div className="space-y-16 pb-8 lg:space-y-20">
      <div className="reference-top">
        <section className="reference-hero">
          <div className="reference-hero-copy">
            <div className="reference-eyebrow"><span className="signal-dot" />Forensic blockchain intelligence</div>
            <h1>Follow the money.<br /><span className="gradient-text">Build the evidence.</span></h1>
            <p className="hero-description">Turn a wallet address into an explainable investigation. Trace transactions, identify likely exchanges, detect risks, and connect every conclusion to its on-chain evidence.</p>
            <div className="hero-wallet-search"><WalletSearch showNetwork /></div>
            <div className="example-chips"><span>Try an example:</span>{DEMO_WALLETS.slice(0,4).map((w,i) => <Link key={w.address} href={`/wallets/${w.address}`} title={w.label}><span className={`example-dot example-dot-${i}`}><Fingerprint size={13} /></span>{shortAddr(w.address,6,4)}</Link>)}</div>
            <div className="hero-benefits">{[{icon:ShieldCheck,title:"Real blockchain data",sub:"Blockscout & multiple chains"},{icon:Zap,title:"Explainable attribution",sub:"Six independent evidence signals"},{icon:FileText,title:"Investigation ready",sub:"Reports & case management"}].map(({icon:Icon,title,sub}) => <div key={title}><Icon size={29} /><span><strong>{title}</strong><small>{sub}</small></span></div>)}</div>
          </div>
          <ReferenceGraph />
        </section>
        <section className="reference-stats" aria-label="Platform capabilities">{STATS.map((s,i) => {const Icon=[Link2,Radio,BarChart3,FlaskConical,Database][i];return <div key={s.l} className="reference-stat"><span className={`stat-icon stat-icon-${i}`}><Icon size={27} /></span><div><strong>{s.n}</strong><span>{s.l}</span><small>{s.sub}</small></div></div>;})}</section>
        <section className="reference-workflow" id="workflow">
          <Eyebrow tone="accent">How ChainTrace investigates</Eyebrow>
          <h2>From a wallet address to actionable intelligence.</h2>
          <p>A transparent, reproducible pipeline for investigations.</p>
          <div className="workflow-steps">{HOW.map((s,i) => <div className="workflow-step" key={s.title}><span className="workflow-icon"><s.icon size={24} /></span><div><h3>{i+1}. {s.title}</h3><p>{s.body}</p></div>{i<3 && <ArrowRight className="workflow-arrow" size={22} />}</div>)}</div>
        </section>
      </div>

      {/* ══════════════════════ 5 · INVESTIGATION PIPELINE ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="Investigation pipeline"
          title="From wallet address to actionable intelligence."
        />
        <Reveal className="mt-10">
          <Tile bodyClassName="p-8 sm:p-10">
            <div className="mx-auto flex max-w-lg flex-col">
              {PIPELINE.map((step, i) => (
                <div key={step.label} className="relative flex items-center gap-4 pb-7 last:pb-0">
                  {i < PIPELINE.length - 1 && (
                    <span className="absolute left-[19px] top-10 h-7 w-px bg-soft-border" />
                  )}
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-soft-border bg-surface-lavender text-primary">
                    <step.icon size={16} />
                  </div>
                  <div className="font-mono text-[13px] text-heading">{step.label}</div>
                </div>
              ))}
            </div>
          </Tile>
        </Reveal>
      </div>

      {/* ══════════════════════ 6 · EVIDENCE SIGNALS ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="Evidence-backed attribution"
          title="Every attribution has a reason."
          sub="ChainTrace does not simply name an exchange. It shows the evidence supporting the conclusion."
        />
        <Reveal className="mt-10">
          <Tile bodyClassName="divide-y divide-soft-border p-0">
            {SIGNALS.map((s, i) => (
              <div key={s.key} className="group flex items-start gap-4 px-6 py-5 transition-colors hover:bg-surface-lavender sm:px-8">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-btn bg-primary-soft text-primary">
                  <s.icon size={16} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-[11px] text-muted">0{i + 1}</span>
                    <span className="text-[14px] font-semibold text-heading">{SIGNAL_LABEL[s.key]}</span>
                  </div>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted">{s.body}</p>
                </div>
              </div>
            ))}
          </Tile>
        </Reveal>
      </div>

      {/* ══════════════════════ 7 · THREE OUTCOMES ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="Three possible outcomes"
          title="ChainTrace doesn't force an answer."
          sub="When the evidence is weak or conflicting, the system says so."
        />
        <Reveal className="mt-10">
          <BentoGrid>
            {/* Attributed */}
            <Tile className="col-span-4" bodyClassName="p-7">
              <Pill tone="good" className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={12} />
                Attributed
              </Pill>
              {attributed?.candidates[0] ? (
                <>
                  <div className="mt-4 font-display text-[22px] font-semibold text-heading">
                    {attributed.candidates[0].vasp_name}
                  </div>
                  <div className="mt-1 font-display text-[38px] font-bold text-good-text">
                    {pct(attributed.candidates[0].probability, 1)}
                  </div>
                  <div className="mt-1 text-[11px] uppercase tracking-wider text-muted">High confidence</div>
                </>
              ) : (
                <div className="mt-4 text-[13px] text-muted">{liveDataFailed ? "Live demo unavailable." : "Loading…"}</div>
              )}
              <p className="mt-4 text-[13px] leading-relaxed text-muted">
                Strong evidence supports the attribution.
              </p>
            </Tile>

            {/* Ambiguous */}
            <Tile className="col-span-4" bodyClassName="p-7">
              <Pill tone="warn" className="inline-flex items-center gap-1.5">
                <Shuffle size={12} />
                Ambiguous
              </Pill>
              {ambiguous?.candidates.length ? (
                <div className="mt-4 space-y-1.5">
                  {ambiguous.candidates.slice(0, 2).map((c) => (
                    <div key={c.vasp_name} className="flex items-center justify-between">
                      <span className="font-display text-[16px] font-semibold text-heading">{c.vasp_name}</span>
                      <span className="font-display text-[16px] font-bold text-warn-text">{pct(c.probability, 0)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 text-[13px] text-muted">{liveDataFailed ? "Live demo unavailable." : "Loading…"}</div>
              )}
              <p className="mt-4 text-[13px] leading-relaxed text-muted">
                Multiple candidates remain plausible.
              </p>
            </Tile>

            {/* Insufficient evidence */}
            <Tile className="col-span-4" bodyClassName="p-7">
              <Pill tone="neutral" className="inline-flex items-center gap-1.5">
                <HelpCircle size={12} />
                Insufficient evidence
              </Pill>
              <div className="mt-4 font-display text-[18px] font-semibold text-heading">
                {insufficient ? "No reliable attribution" : liveDataFailed ? "Live demo unavailable." : "Loading…"}
              </div>
              <p className="mt-4 text-[13px] leading-relaxed text-muted">
                Available evidence does not support a confident VASP match.
              </p>
            </Tile>
          </BentoGrid>
          <p className="mt-6 text-center text-[12px] text-muted">
            Confidence thresholds prevent ChainTrace from forcing an unsupported attribution.
          </p>
        </Reveal>
      </div>

      {/* ══════════════════════ 8 · LIVE FORENSIC GRAPH ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="Live forensic graph"
          title="See the money move."
          sub="Explore the transaction path, connected wallets, and VASP relationships behind an attribution."
        />
        <Reveal className="mt-10">
          {showcaseGraph ? (
            <GraphView
              graph={showcaseGraph}
              highlightedTx={new Set()}
              highlightedNode={null}
              riskAddresses={riskAddresses}
              onNodeFocus={(addr) => router.push(`/wallets/${addr}`)}
            />
          ) : (
            <Tile bodyClassName="p-10 text-center">
              <p className="text-[13px] text-muted">
                {liveDataFailed ? "Live demo graph unavailable — start the backend to see it here." : "Loading live demo graph…"}
              </p>
            </Tile>
          )}
          <div className="mt-6 flex justify-center">
            <Link href={`/wallets/${OUTCOME_WALLETS.attributed.address}`}>
              <Button variant="secondary" className="flex items-center gap-2">
                Explore a trace
                <ArrowRight size={15} />
              </Button>
            </Link>
          </div>
        </Reveal>
      </div>

      {/* ══════════════════════ 9 · RISK INTELLIGENCE ══════════════════════ */}
      <div id="analytics" className="scroll-mt-28">
        <SectionHead
          eyebrow="Risk intelligence"
          title="Who it is is only half the answer."
          sub="Attribution and risk are calculated independently."
        />
        <Reveal className="mt-10">
          <BentoGrid>
            <Tile className="col-span-4 md:col-span-5" bodyClassName="p-7">
              <Eyebrow>Risk score</Eyebrow>
              {showcaseRisk ? (
                <div className="mt-3 flex items-end gap-3">
                  <span className="font-display text-[44px] font-bold text-heading">
                    {Math.round(showcaseRisk.score * 100)}
                  </span>
                  <span className="pb-1.5 text-[13px] text-muted">/ 100</span>
                  <span className="ml-auto pb-1.5 text-[14px] font-medium text-warn-text">{showcaseRisk.level}</span>
                </div>
              ) : (
                <div className="mt-3 text-[13px] text-muted">{liveDataFailed ? "Live demo unavailable." : "Loading…"}</div>
              )}
              <div className="mt-5 flex flex-wrap gap-1.5">
                {(showcaseRisk?.typology_tags.length
                  ? showcaseRisk.typology_tags.map((t) => t.category.replace("_", " "))
                  : ["LAYERING", "SANCTIONED COUNTERPARTY", "RAPID MOVEMENT", "PEEL CHAIN"]
                ).map((t) => (
                  <Pill key={t} tone="warn">{t}</Pill>
                ))}
              </div>
            </Tile>
            <Tile className="col-span-4 md:col-span-7" bodyClassName="p-7">
              <Eyebrow>Independent of attribution</Eyebrow>
              <p className="mt-3 text-[14px] leading-relaxed text-body">
                Risk analysis considers suspicious transaction patterns, sanctioned counterparties,
                mixer exposure, and other typologies — independently of attribution confidence. A
                wallet can be confidently attributed to an exchange <em>and</em> flagged high-risk at
                the same time; one score never implies the other.
              </p>
            </Tile>
          </BentoGrid>
        </Reveal>
      </div>

      {/* ══════════════════════ 10 · MULTI-CHAIN ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="One workflow. Multiple chains."
          title="Investigate supported blockchain networks without changing the workflow."
        />
        <Reveal className="mt-10">
          <BentoGrid>
            {CHAINS.map((c) => (
              <Tile key={c.name} className="col-span-4 md:col-span-6" bodyClassName="flex items-center gap-4 p-7">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-btn bg-primary-soft text-primary">
                  <c.icon size={19} />
                </div>
                <div>
                  <div className="font-display text-[17px] font-semibold text-heading">{c.name}</div>
                  <div className="mt-1 flex gap-1.5">
                    {c.assets.map((a) => (
                      <Pill key={a} tone="muted">{a}</Pill>
                    ))}
                  </div>
                </div>
              </Tile>
            ))}
          </BentoGrid>
        </Reveal>
      </div>

      {/* ══════════════════════ 11 · VASP INTELLIGENCE ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="VASP intelligence"
          title="Investigate the network behind the exchange."
          sub="Explore VASP deposit addresses, sweep behaviour, and connected wallet clusters."
        />
        <Reveal className="mt-10">
          <Tile bodyClassName="p-7 sm:p-8">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-btn bg-primary-soft text-primary">
                <Landmark size={18} />
              </div>
              <div>
                <div className="font-display text-[17px] font-semibold text-heading">
                  {attributed?.candidates[0]?.vasp_name ?? "Binance"}
                </div>
                <div className="text-[11px] uppercase tracking-wider text-muted">from a live demo trace</div>
              </div>
            </div>
            <p className="mt-4 max-w-2xl text-[13px] leading-relaxed text-body">
              {showcaseEvidence?.description ??
                (liveDataFailed
                  ? "Live demo evidence unavailable — start the backend to see a real deposit-sweep cluster here."
                  : "Loading real evidence from the demo trace…")}
            </p>
            <div className="mt-5">
              <Link href={`/wallets/${OUTCOME_WALLETS.attributed.address}`} className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline">
                Explore this cluster in a trace
                <ArrowRight size={13} />
              </Link>
            </div>
          </Tile>
        </Reveal>
      </div>

      {/* ══════════════════════ 12 · SAHYOG / ACTION ══════════════════════ */}
      <div>
        <SectionHead
          eyebrow="From attribution to action"
          title="From attribution to investigative action."
          sub="Once a VASP attribution is established, ChainTrace can prepare a structured lawful disclosure request."
        />
        <Reveal className="mt-10">
          <Tile bodyClassName="p-7 sm:p-8">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {SAHYOG_FIELDS.map((f) => (
                <div key={f} className="flex items-center gap-2.5 text-[13px] text-body">
                  <Scale size={13} className="shrink-0 text-primary" />
                  {f}
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-soft-border pt-6">
              <Link href="/trace">
                <Button variant="primary" className="flex items-center gap-2">
                  Start a trace to prepare one
                  <ArrowRight size={15} />
                </Button>
              </Link>
              <p className="text-[12px] text-muted">
                ChainTrace prepares the draft. Portal submission remains subject to authorized
                government access.
              </p>
            </div>
          </Tile>
        </Reveal>
      </div>

      {/* ══════════════════════ 13 · REAL DEMO CASES ══════════════════════ */}
      <div>
        <SectionHead eyebrow="See ChainTrace in action" title="Real demo cases." />
        <Reveal className="mt-10">
          <BentoGrid>
            {DEMO_WALLETS.map((w, i) => (
              <Tile key={w.address} interactive className="col-span-4 md:col-span-4" bodyClassName="p-6">
                <Link href={`/wallets/${w.address}`} className="group flex h-full flex-col">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase text-muted">
                      CASE-{String(i + 1).padStart(2, "0")} · {chainOf(w.address)}
                    </span>
                  </div>
                  <div className="mt-3 font-display text-[16px] font-semibold text-heading group-hover:text-primary">
                    {w.label}
                  </div>
                  <Pill tone="muted" className="mt-2 w-fit">{w.note}</Pill>
                  <div className="mt-3 inline-block w-fit rounded-lg bg-surface-lavender px-2.5 py-1 font-mono text-xs text-mono">
                    {shortAddr(w.address, 10, 8)}
                  </div>
                  <div className="mt-auto pt-4 text-[11px] text-muted transition-colors group-hover:text-primary">
                    open investigation →
                  </div>
                </Link>
              </Tile>
            ))}
          </BentoGrid>
        </Reveal>
      </div>

      {/* ══════════════════════ 14 · TRANSPARENCY ══════════════════════ */}
      <div id="documentation" className="scroll-mt-28">
        <SectionHead eyebrow="Built for transparency" title="Honest about what ChainTrace can and can't do." />
        <Reveal className="mt-10">
          <BentoGrid>
            {TRANSPARENCY.map((t) => (
              <Tile key={t.title} className="col-span-4 md:col-span-6" bodyClassName="p-6">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={15} className="text-primary" />
                  <span className="text-[13px] font-semibold uppercase tracking-wider text-heading">{t.title}</span>
                </div>
                <p className="mt-2 text-[13px] leading-relaxed text-muted">{t.body}</p>
              </Tile>
            ))}
          </BentoGrid>
        </Reveal>
      </div>

      {/* ══════════════════════ 15 · FINAL CTA ══════════════════════ */}
      <Reveal>
        <Tile bodyClassName="p-12 text-center sm:p-16">
          <Sparkles size={20} className="mx-auto text-primary" />
          <h2 className="mx-auto mt-4 max-w-lg font-display text-[28px] font-semibold leading-[1.2] text-heading sm:text-[34px]">
            Start with a wallet address.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-[14px] text-body">
            Trace the flow. Examine the evidence. Understand the risk.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link href="/trace">
              <Button variant="primary" className="flex items-center gap-2">
                Trace a wallet
                <ArrowRight size={15} />
              </Button>
            </Link>
            <Link href="/trace">
              <Button variant="secondary" className="flex items-center gap-2">
                View demo cases
                <ArrowRight size={15} />
              </Button>
            </Link>
          </div>
        </Tile>
      </Reveal>

      {/* ══════════════════════ FOOTER ══════════════════════ */}
      <footer className="border-t border-soft-border pt-8">
        <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:justify-between sm:text-left">
          <div>
            <div className="font-display text-[14px] font-bold text-heading">
              CHAIN<span className="text-primary">TRACE</span>
            </div>
            <div className="mt-0.5 text-[12px] text-muted">Blockchain forensic intelligence</div>
          </div>
          <nav className="flex items-center gap-5 text-[12px] text-muted">
            <Link href="/trace" className="hover:text-heading">Trace</Link>
            <Link href="/cases" className="hover:text-heading">Cases</Link>
          </nav>
          <div className="flex items-center gap-1.5">
            <Pill tone="muted">Ethereum</Pill>
            <Pill tone="muted">Tron</Pill>
            <Pill tone="muted">ERC-20</Pill>
            <Pill tone="muted">USDT-TRC20</Pill>
          </div>
        </div>
        <p className="mt-6 text-center text-[11px] text-muted sm:text-left">
          Built for evidence-backed blockchain investigation.
        </p>
      </footer>
    </div>
  );
}
