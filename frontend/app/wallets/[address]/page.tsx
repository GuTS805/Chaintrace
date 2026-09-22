"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, Check, Copy, Download, Scale } from "lucide-react";
import { api } from "@/lib/api";
import type { AttributionResult, GraphResult, RiskResult } from "@/lib/types";
import { pushRecent } from "@/lib/recents";
import { AttributionPanel } from "@/components/AttributionPanel";
import { RiskPanel } from "@/components/RiskPanel";
import { GraphView } from "@/components/GraphView";
import { NodeFocusDrawer } from "@/components/NodeFocusDrawer";
import { AddToCase } from "@/components/AddToCase";
import { WalletSearch } from "@/components/WalletSearch";
import { LiveTrace } from "@/components/LiveTrace";
import { PdfButton } from "@/components/PdfButton";
import { BentoGrid, Button, Eyebrow, Tile } from "@/components/ui";

/** Staggered fade+rise entrance for the verdict → graph → risk reading order. */
function FadeIn({ index, children }: { index: number; children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

export default function WalletPage({
  params,
}: {
  params: { address: string };
}) {
  const decoded = decodeURIComponent(params.address);
  // EVM addresses are case-insensitive hex; Tron (and other base58) addresses
  // are case-sensitive/checksummed and must not be lowercased.
  const address = decoded.toLowerCase().startsWith("0x") ? decoded.toLowerCase() : decoded;
  // A live trace tells us the real chain queried; until then, EVM addresses
  // default to "ethereum" in the badge.
  const [resolvedChain, setResolvedChain] = useState<string | null>(null);
  const chain = (resolvedChain ?? (address.startsWith("T") ? "tron" : "ethereum")).toUpperCase();
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [graph, setGraph] = useState<GraphResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [partial, setPartial] = useState(false);
  async function copyAddress() {
    try { await navigator.clipboard.writeText(address); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  useEffect(() => { if (!copied) return; const timer = setTimeout(() => setCopied(false), 2000); return () => clearTimeout(timer); }, [copied]);

  // Cross-highlight state, shared by AttributionPanel/RiskPanel (source) and
  // GraphView (destination).
  const [highlightedTx, setHighlightedTx] = useState<Set<string>>(new Set());
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const [focusedNode, setFocusedNode] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setAttribution(null); setRisk(null); setGraph(null); setPartial(false);
    const results = await Promise.allSettled([
      api.attribution(address),
      api.risk(address),
      api.graph(address, 5),
    ]);
    const [a, r, g] = results;
    setPartial(results.some(x => x.status === "rejected") && results.some(x => x.status === "fulfilled"));
    if (a.status === "fulfilled") setAttribution(a.value);
    if (r.status === "fulfilled") setRisk(r.value);
    if (g.status === "fulfilled") setGraph(g.value);
    if (results.every((x) => x.status === "rejected")) {
      const first = results.find((x) => x.status === "rejected") as
        | PromiseRejectedResult
        | undefined;
      setError(
        first ? String(first.reason) : "Could not reach the API. Is it running?",
      );
    }
    setLoading(false);
  }, [address]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!loading && !error) pushRecent(address);
  }, [address, loading, error]);

  // A wallet with no local data: no candidates and an empty graph.
  const isEmpty =
    (attribution?.candidates.length ?? 0) === 0 &&
    (graph?.nodes.length ?? 0) <= 1;

  const riskAddresses = new Set(risk?.indicators.map((i) => i.address) ?? []);

  return (
    <div className="space-y-10">
      <div className="page-intro flex flex-wrap items-end justify-between gap-6">
        <div>
          <Link href="/trace" className="mb-5 inline-flex items-center gap-2 text-xs text-muted hover:text-primary"><ArrowLeft size={14} /> Wallet tracing</Link>
          <Eyebrow>Trace wallet · {chain}</Eyebrow>
          <h1 className="mt-2 font-display text-2xl font-semibold text-heading">Wallet investigation</h1>
          <div className="mt-3 flex items-center gap-3"><span className="break-all font-mono text-xs text-mono sm:text-sm">{address}</span><button type="button" onClick={() => void copyAddress()} aria-label={copied ? "Address copied" : "Copy wallet address"} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-btn border border-soft-border text-muted hover:text-primary">{copied ? <Check size={16} /> : <Copy size={16} />}</button></div>
          <span role="status" className="text-xs text-muted">{copied ? "Address copied" : copyError ? "Copy unavailable. Select the address to copy it manually." : ""}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PdfButton
            path={`/wallets/${address}/report`}
            className="flex items-center gap-1.5 rounded-btn border border-soft-border px-3 py-2 text-[12px] text-muted transition-all hover:bg-surface-lavender hover:text-heading"
          >
            <Download size={13} />
            Report (PDF)
          </PdfButton>
          {attribution &&
            !attribution.insufficient_evidence &&
            attribution.candidates.length > 0 && (
              <PdfButton
                path={`/wallets/${address}/disclosure-request`}
                className="flex items-center gap-1.5 action-primary rounded-btn bg-primary px-3 py-2 text-[12px] font-medium text-[#091126] shadow-button transition-all hover:-translate-y-0.5 hover:bg-primary-hover active:translate-y-0"
              >
                <Scale size={13} />
                Prepare disclosure request (SAHYOG)
              </PdfButton>
            )}
        </div>
      </div>

      <div className="max-w-md">
        <WalletSearch />
      </div>

      {loading && <div role="status" aria-label="Loading wallet investigation" className="grid gap-5 md:grid-cols-2">{[0, 1].map(i => <div key={i} className="h-64 animate-pulse rounded-card border border-soft-border bg-surface p-6"><div className="h-3 w-28 rounded bg-neutral-fill" /><div className="mt-6 h-8 w-1/2 rounded bg-neutral-fill" /><div className="mt-5 h-24 rounded bg-neutral-fill" /></div>)}<span className="sr-only">Tracing transactions and collecting evidence...</span></div>}
      {partial && !loading && <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-btn border border-warn-text/20 bg-warn-fill p-4"><p className="text-sm text-warn-text">Some evidence could not be loaded. Results below are incomplete.</p><Button onClick={() => void load()}>Retry</Button></div>}
      {error && (
        <Tile title="Investigation unavailable">
          <p role="alert" className="text-sm text-bad-text">{error}</p>
          <p className="mt-2 text-sm text-muted">The investigation service could not return this wallet. Retry to reconnect.</p>
          <Button onClick={() => void load()} className="mt-4">Retry investigation</Button>
        </Tile>
      )}

      {!loading && !error && !partial && isEmpty && (
        <LiveTrace
          address={address}
          onDone={(usedChain) => {
            setResolvedChain(usedChain);
            void load();
          }}
        />
      )}

      {!loading && !error && !isEmpty && (
        <div className="space-y-10">
          {/* Details on the left, the graph on the right — the evidence
              chain and the diagram it references, side by side. */}
          <BentoGrid>
            <div className="col-span-4 md:col-span-5">
              {attribution && (
                <FadeIn index={0}>
                  <AttributionPanel
                    result={attribution}
                    onHoverEvidence={(hashes) => setHighlightedTx(new Set(hashes ?? []))}
                  />
                </FadeIn>
              )}
            </div>
            <div className="col-span-4 md:col-span-7">
              {graph && (
                <FadeIn index={1}>
                  <GraphView
                    graph={graph}
                    highlightedTx={highlightedTx}
                    highlightedNode={highlightedNode}
                    riskAddresses={riskAddresses}
                    onNodeFocus={(addr, isRoot) => {
                      if (!isRoot) setFocusedNode(addr);
                    }}
                  />
                </FadeIn>
              )}
            </div>
          </BentoGrid>

          <FadeIn index={2}>
            <BentoGrid>
              <div className="col-span-4 md:col-span-7">
                {risk && (
                  <RiskPanel
                    risk={risk}
                    onHoverIndicator={(addr) => setHighlightedNode(addr)}
                  />
                )}
              </div>
              <div className="col-span-4 md:col-span-5">
                <AddToCase address={address} attribution={attribution} />
              </div>
            </BentoGrid>
          </FadeIn>
        </div>
      )}

      <AnimatePresence>
        {focusedNode && (
          <NodeFocusDrawer key={focusedNode} address={focusedNode} onClose={() => setFocusedNode(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
