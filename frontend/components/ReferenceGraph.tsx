"use client";

import { useState } from "react";
import { Activity, Clock3, GitBranch, Layers3, ShieldAlert } from "lucide-react";

const tabs = ["Graph View", "Attribution", "Risk Signals"] as const;
export function ReferenceGraph() {
  const [tab, setTab] = useState<typeof tabs[number]>("Graph View");
  return (
    <section className="reference-graph" aria-label="Illustrative transaction intelligence preview">
      <div className="reference-graph-heading">
        <span className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[.15em] text-heading"><span className="signal-dot" />Transaction intelligence</span>
        <div role="tablist" aria-label="Intelligence preview" className="graph-tabs">
          {tabs.map(t => <button key={t} id={`preview-tab-${t.replaceAll(" ", "-")}`} role="tab" aria-selected={tab === t} aria-controls="preview-panel" onClick={() => setTab(t)} onKeyDown={e => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); const next = tabs[(tabs.indexOf(t) + (e.key === "ArrowRight" ? 1 : 2)) % tabs.length]; setTab(next); document.getElementById(`preview-tab-${next.replaceAll(" ", "-")}`)?.focus(); } }} tabIndex={tab === t ? 0 : -1}>{t}</button>)}
        </div>
      </div>
      <div id="preview-panel" role="tabpanel" aria-labelledby={`preview-tab-${tab.replaceAll(" ", "-")}`} className="preview-panel">
        {tab === "Graph View" ? <svg viewBox="0 0 710 302" className="branching-graph" role="img" aria-label="Illustrative subject wallet connected through intermediary wallets to Kraken, Binance, and an unknown destination">
          <defs>
            <linearGradient id="branch-line"><stop stopColor="#29c9fa" /><stop offset="1" stopColor="#b18bff" /></linearGradient>
            <linearGradient id="branch-card" x2="1" y2="1"><stop stopColor="#131c35" /><stop offset="1" stopColor="#091727" /></linearGradient>
            <radialGradient id="branch-glow"><stop stopColor="#1258a6" stopOpacity=".32" /><stop offset="1" stopColor="#1258a6" stopOpacity="0" /></radialGradient>
            <radialGradient id="dot-cyan"><stop stopColor="#a5ffff" /><stop offset="1" stopColor="#08b9f0" /></radialGradient>
            <radialGradient id="dot-purple"><stop stopColor="#e4d0ff" /><stop offset="1" stopColor="#8655f4" /></radialGradient>
          </defs>
          <ellipse cx="285" cy="152" rx="280" ry="160" fill="url(#branch-glow)" />
          <g fill="none" stroke="url(#branch-line)" strokeWidth="1.2" opacity=".8">
            <path d="M150 151 C183 151 182 79 220 79 S268 44 304 44 S373 98 410 98 S469 54 514 54" />
            <path d="M150 151 C204 151 231 139 283 139 S368 99 410 98 S468 147 514 147" />
            <path d="M150 170 C216 170 231 226 296 226 S354 191 391 191 S467 241 514 241" />
          </g>
          <g className="network-packets" fill="#9beaff">
            <circle r="3"><animateMotion dur="7s" repeatCount="indefinite" path="M150 151 C183 151 182 79 220 79 S268 44 304 44 S373 98 410 98 S469 54 514 54" /></circle>
            <circle r="3"><animateMotion dur="5s" repeatCount="indefinite" path="M150 151 C204 151 231 139 283 139 S368 99 410 98 S468 147 514 147" /></circle>
            <circle r="3"><animateMotion dur="6s" repeatCount="indefinite" path="M150 170 C216 170 231 226 296 226 S354 191 391 191 S467 241 514 241" /></circle>
          </g>
          <g strokeWidth="2" className="graph-junctions"><circle cx="220" cy="79" r="8" fill="url(#dot-cyan)" stroke="#5edcff" /><circle cx="304" cy="44" r="7" fill="url(#dot-purple)" stroke="#c8a6ff" /><circle cx="410" cy="98" r="8" fill="url(#dot-purple)" stroke="#c4beff" /><circle cx="283" cy="139" r="8" fill="#2966d8" stroke="#86c2ff" /><circle cx="296" cy="226" r="8" fill="#3274e3" stroke="#83b9ff" /><circle cx="391" cy="191" r="8" fill="#146c9d" stroke="#39e0ff" /></g>
          <rect x="16" y="112" width="136" height="104" rx="20" fill="url(#branch-card)" stroke="#9b82fb" />
          <g fill="none" stroke="#74d2ff" strokeWidth="2"><rect x="40" y="136" width="27" height="20" rx="3" /><path d="M40 140 V132 H64 V136 M60 144 H70 V151 H60 Z" /></g>
          <g fontFamily="Segoe UI, sans-serif" fill="#f0f2ff"><text x="39" y="181" fontSize="11" fontWeight="600">Subject Wallet</text><text x="39" y="200" fontSize="10" fill="#b8c3e5">0x52f9...148</text></g>
          {[{ y: 0, name: "Kraken", detail: "Confidence: 70%", color: "#a98aff", width: 48, letter: "K" }, { y: 94, name: "Binance", detail: "Confidence: 90%", color: "#42e8c5", width: 81, letter: "B" }, { y: 188, name: "Unknown", detail: "Insufficient evidence", color: "#8290ad", width: 24, letter: "?" }].map(c => <g key={c.name} transform={`translate(514 ${c.y + 16})`}><rect width="181" height="75" rx="18" fill="url(#branch-card)" stroke="#55637e" strokeOpacity=".8" /><circle cx="30" cy="32" r="17" fill={c.name === "Kraken" ? "#45339f" : c.name === "Binance" ? "#323021" : "#253149"} /><text x="30" y="38" textAnchor="middle" fill={c.name === "Binance" ? "#f8d34b" : "#d6d9ff"} fontSize="18" fontWeight="700" fontFamily="Segoe UI, sans-serif">{c.letter}</text><text x="64" y="25" fill="#f0f2ff" fontSize="11" fontWeight="600" fontFamily="Segoe UI, sans-serif">{c.name}</text><text x="64" y="42" fill="#bac6dc" fontSize="10" fontFamily="Segoe UI, sans-serif">{c.detail}</text><rect x="64" y="53" width="93" height="5" rx="3" fill="#24334a" /><rect x="64" y="53" width={c.width} height="5" rx="3" fill={c.color} /></g>)}
        </svg> : tab === "Attribution" ? <div className="preview-explanation"><span className="text-xs uppercase tracking-widest text-primary">Explainable outcomes</span><h3>Confidence backed by evidence.</h3>{[{name:"Attributed",detail:"Strong signals identify a likely exchange.",width:"90%",color:"#42e8c5"},{name:"Ambiguous",detail:"Multiple candidates remain plausible.",width:"55%",color:"#b899ff"},{name:"Insufficient",detail:"Evidence is too limited for a reliable match.",width:"22%",color:"#8290ad"}].map(r => <div key={r.name} className="mt-4"><div className="flex justify-between gap-3 text-xs"><span className="text-heading">{r.name}</span><span className="text-muted">{r.detail}</span></div><div className="mt-2 h-1 rounded bg-white/5"><div className="h-full rounded" style={{width:r.width,background:r.color}} /></div></div>)}</div> : <div className="preview-explanation"><span className="text-xs uppercase tracking-widest text-primary">Independent risk assessment</span><h3>Know what deserves a closer look.</h3>{["Sanctioned counterparties", "Mixer and bridge exposure", "Layering and rapid movement"].map(t => <div key={t} className="mt-4 flex items-center gap-3 rounded-xl border border-soft-border bg-white/[.025] p-3 text-sm text-body"><ShieldAlert size={18} className="text-info-text" />{t}</div>)}</div>}
      </div>
      <div className="graph-metric-strip">{[{icon:Activity,value:"1,248",label:"Example transfers"},{icon:GitBranch,value:"6",label:"Attribution signals"},{icon:Layers3,value:"3",label:"Example hop depth"},{icon:Clock3,value:"2",label:"Supported chains"}].map(({icon:Icon,value,label}) => <div key={label}><Icon size={23} /><span><strong>{value}</strong><small>{label}</small></span></div>)}</div>
      <p className="graph-preview-caption">Illustrative example &middot; explore a real investigation below</p>
    </section>
  );
}
