"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FolderOpen, Plus, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { CaseOut, CaseStatus } from "@/lib/types";
import { BentoGrid, Button, Eyebrow, Tile, Pill } from "@/components/ui";
import { fmtTime } from "@/lib/format";

const STATUS_TONE: Record<CaseStatus, "good" | "warn" | "muted"> = { OPEN: "good", IN_REVIEW: "warn", CLOSED: "muted" };

export default function CasesPage() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [name, setName] = useState("");
  const [investigator, setInvestigator] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try { setCases(await api.listCases()); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load cases."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true); setError(null); setNotice("");
    try {
      await api.createCase({ name: name.trim(), investigator: investigator.trim() || undefined });
      setName(""); setInvestigator(""); setNotice("Case created. Open it below to start recording evidence.");
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to create case."); }
    finally { setCreating(false); }
  }
  const visible = cases.filter(c => (status === "ALL" || c.status === status) && `${c.name} ${c.investigator ?? ""} CT-${String(c.id).padStart(4, "0")}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="space-y-8">
    <section className="page-intro"><Eyebrow tone="accent">Investigation / Case workspace</Eyebrow><h1 className="mt-3 font-display text-3xl font-semibold tracking-tight text-heading sm:text-4xl">Keep the evidence together.</h1><p className="mt-3 max-w-2xl text-sm leading-relaxed text-body">Organize wallets, findings, and investigator notes into a clear case record, ready for review and reporting.</p>
      <div className="mt-6 flex flex-wrap gap-x-8 gap-y-3 border-t border-soft-border pt-5">{[{ label: "Total cases", value: cases.length }, { label: "Open", value: cases.filter(c => c.status === "OPEN").length }, { label: "In review", value: cases.filter(c => c.status === "IN_REVIEW").length }, { label: "Closed", value: cases.filter(c => c.status === "CLOSED").length }].map(s => <div key={s.label} className="flex items-baseline gap-2"><span className="font-display text-2xl font-semibold text-heading">{loading || error ? "--" : s.value}</span><span className="text-xs text-muted">{s.label}</span></div>)}</div>
    </section>
    <Tile title="Create an investigation" bodyClassName="p-5 sm:p-6"><form onSubmit={create} className="grid items-end gap-4 sm:grid-cols-[1fr_1fr_auto]"><label className="block text-xs font-medium text-body">Case name <span className="text-primary">*</span><input required value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Ransomware investigation" className="mt-2 h-12 w-full rounded-input border border-soft-border bg-surface-lavender px-3 text-sm text-heading" /></label><label className="block text-xs font-medium text-body">Investigator <span className="font-normal text-muted">(optional)</span><input value={investigator} onChange={e => setInvestigator(e.target.value)} placeholder="Officer name" className="mt-2 h-12 w-full rounded-input border border-soft-border bg-surface-lavender px-3 text-sm text-heading" /></label><Button type="submit" variant="primary" disabled={creating || !name.trim()} className="flex h-12 items-center justify-center gap-2"><Plus size={16} />{creating ? "Creating..." : "Create case"}</Button></form></Tile>
    {notice && <p role="status" className="rounded-btn border border-good-text/20 bg-good-fill p-4 text-sm text-good-text">{notice}</p>}
    {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-btn border border-bad-text/20 bg-bad-fill p-4"><p className="text-sm text-bad-text">{error}</p><Button onClick={() => void load()}>Retry loading</Button></div>}
    <section><div className="mb-5 flex flex-wrap items-center justify-between gap-4"><h2 className="font-display text-xl font-semibold text-heading">Case records <span className="ml-2 text-sm font-normal text-muted">{loading ? "" : `(${visible.length})`}</span></h2><div className="flex w-full flex-wrap gap-2 sm:w-auto"><div className="relative flex-1"><Search size={15} className="absolute left-3 top-3.5 text-muted" /><input aria-label="Search cases" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search name, officer, or ID" className="h-11 w-full rounded-btn border border-soft-border bg-surface pl-9 pr-3 text-xs text-heading sm:w-60" /></div><select aria-label="Filter by case status" value={status} onChange={e => setStatus(e.target.value)} className="h-11 rounded-btn border border-soft-border bg-surface px-3 text-xs text-heading"><option value="ALL">All statuses</option><option value="OPEN">Open</option><option value="IN_REVIEW">In review</option><option value="CLOSED">Closed</option></select></div></div>
    {loading ? <div role="status" aria-label="Loading cases" className="grid gap-4 sm:grid-cols-3">{[0,1,2].map(i => <div key={i} className="h-44 animate-pulse rounded-card border border-soft-border bg-surface p-6"><div className="h-3 w-20 rounded bg-neutral-fill" /><div className="mt-6 h-5 w-3/4 rounded bg-neutral-fill" /><div className="mt-3 h-3 w-1/2 rounded bg-neutral-fill" /></div>)}</div> : !error && visible.length === 0 ? <Tile bodyClassName="p-10 text-center"><FolderOpen size={32} className="mx-auto text-primary" /><h3 className="mt-4 font-display text-lg font-semibold text-heading">{cases.length ? "No matching cases" : "Your next investigation starts here"}</h3><p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">{cases.length ? "Try a different search or status filter." : "Create a case above, then add wallets and findings as your investigation develops."}</p>{cases.length > 0 && <Button className="mt-4" onClick={() => { setQuery(""); setStatus("ALL"); }}>Clear filters</Button>}</Tile> : <BentoGrid>{visible.map(c => <Tile key={c.id} interactive className="col-span-4" bodyClassName="p-0"><Link href={`/cases/${c.id}`} className="group flex h-full flex-col p-6"><div className="flex items-center justify-between gap-2"><span className="font-mono text-xs text-muted">CT-{String(c.id).padStart(4, "0")}</span><Pill tone={STATUS_TONE[c.status]}>{c.status.replaceAll("_", " ")}</Pill></div><h3 className="mt-5 break-words font-display text-lg font-semibold text-heading group-hover:text-primary">{c.name}</h3><p className="mt-2 text-xs text-muted">{c.investigator || "No investigator assigned"}</p><div className="mt-auto flex items-center justify-between border-t border-soft-border pt-4 mt-5"><span className="text-[11px] text-muted">{fmtTime(c.created_at)} UTC</span><ArrowRight size={16} className="text-primary" /></div></Link></Tile>)}</BentoGrid>}
    </section>
  </div>;
}
