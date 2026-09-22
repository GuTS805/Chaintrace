"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Fingerprint, FlaskConical, Network, Search } from "lucide-react";
import { WalletSearch } from "@/components/WalletSearch";
import { Eyebrow, Pill, BentoGrid, Tile } from "@/components/ui";
import { DEMO_WALLETS, shortAddr } from "@/lib/format";

export default function TracePage() {
  const [filter, setFilter] = useState("All examples");
  const examples = DEMO_WALLETS.map((wallet, index) => ({ ...wallet, index })).filter(w => filter === "All examples" || (filter === "Real-chain snapshots" ? w.note.startsWith("real:") : !w.note.startsWith("real:")));
  return <div className="space-y-10">
    <section className="page-intro grid items-center gap-8 lg:grid-cols-[1fr_300px]">
      <div>
        <Eyebrow tone="accent">Investigation / Wallet tracing</Eyebrow>
        <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight text-heading sm:text-4xl">One address. A trail of evidence.</h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-body">Enter an Ethereum, Polygon, or Tron wallet to explore its activity, identify likely exchanges, and assess risk.</p>
        <div className="mt-6 max-w-2xl"><WalletSearch autoFocus /></div>
        <p className="mt-3 text-xs text-muted">Use a 0x address for EVM networks or a T address for Tron.</p>
      </div>
      <div className="space-y-5 border-t border-soft-border pt-6 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">{[
        { icon: Search, title: "Trace the flow", text: "Explore connected wallets and transfers." },
        { icon: Fingerprint, title: "Examine the signals", text: "Understand the basis for each attribution." },
        { icon: Network, title: "Build your case", text: "Save findings and export a report." },
      ].map(({ icon: Icon, title, text }, i) => <div key={title} className="flex gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-btn bg-primary-soft text-primary"><Icon size={17} /></span><div><div className="text-sm font-medium text-heading"><span className="mr-2 text-xs text-muted">0{i + 1}</span>{title}</div><p className="mt-1 text-xs leading-relaxed text-muted">{text}</p></div></div>)}</div>
    </section>
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4"><div><Eyebrow>Explore the workflow</Eyebrow><h2 className="mt-2 font-display text-xl font-semibold text-heading">Example investigations</h2><p className="mt-2 text-sm text-muted">Seeded scenarios and real-chain snapshots with different attribution outcomes.</p></div><span className="flex items-center gap-2 text-xs text-muted"><FlaskConical size={15} />{examples.length} examples</span></div>
      <div className="my-6 flex flex-wrap gap-2" role="group" aria-label="Filter example investigations">{["All examples", "Seeded scenarios", "Real-chain snapshots"].map(item => <button key={item} type="button" aria-pressed={filter === item} onClick={() => setFilter(item)} className={`min-h-10 rounded-btn border px-4 text-xs font-medium transition-colors ${filter === item ? "border-primary/30 bg-primary-soft text-primary" : "border-soft-border text-muted hover:text-heading"}`}>{item}</button>)}</div>
      <BentoGrid>{examples.map(w => <Tile key={w.address} interactive className="col-span-4" bodyClassName="p-0"><Link href={`/wallets/${w.address}`} className="group flex h-full flex-col p-6"><div className="flex items-center justify-between"><span className="font-mono text-[11px] text-muted">EXAMPLE {String(w.index + 1).padStart(2, "0")}</span><Pill tone={w.address.startsWith("T") ? "good" : "info"}>{w.address.startsWith("T") ? "Tron" : "Ethereum"}</Pill></div><h3 className="mt-5 font-display text-lg font-semibold text-heading transition-colors group-hover:text-primary">{w.label}</h3><p className="mt-2 text-xs text-muted">{w.note}</p><div className="mt-5 rounded-lg border border-soft-border bg-[#0D1025] px-3 py-2 font-mono text-xs text-mono">{shortAddr(w.address, 10, 8)}</div><div className="mt-auto flex items-center justify-between pt-5 text-xs font-medium text-primary">Open investigation<ArrowRight size={16} className="transition-transform group-hover:translate-x-1" /></div></Link></Tile>)}</BentoGrid>
      <p className="mt-6 text-xs leading-relaxed text-muted">Example data is preloaded for repeatable investigations. Save evidence in your <Link href="/cases" className="text-primary hover:underline">case workspace</Link>.</p>
    </section>
  </div>;
}
