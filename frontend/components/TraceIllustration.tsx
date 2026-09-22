import { ArrowUpRight, Fingerprint, Layers3, ShieldCheck } from "lucide-react";

/** Decorative workflow diagram; does not represent live transaction data. */
export function TraceIllustration() {
  return (
    <div className="trace-scene relative overflow-hidden rounded-hero border border-soft-border">
      <div className="relative z-10 flex items-center justify-between gap-2 px-5 pt-5 sm:px-7 sm:pt-7">
        <span className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.17em] text-body"><span className="signal-dot" />Transaction intelligence</span>
        <span className="rounded-full border border-info-text/25 bg-info-fill px-2.5 py-1 text-[9px] uppercase tracking-wider text-info-text">Workflow preview</span>
      </div>
      <div className="network-art relative" aria-hidden="true">
        <svg viewBox="0 0 600 340" className="block w-full">
          <defs>
            <linearGradient id="network-line" x1="0" x2="1"><stop stopColor="#67e8f9" /><stop offset=".5" stopColor="#a78bfa" /><stop offset="1" stopColor="#f0abfc" /></linearGradient>
            <radialGradient id="network-halo"><stop stopColor="#8b5cf6" stopOpacity=".28" /><stop offset="1" stopColor="#8b5cf6" stopOpacity="0" /></radialGradient>
          </defs>
          <circle cx="300" cy="166" r="160" fill="url(#network-halo)" />
          <g fill="none" stroke="#a78bfa" strokeOpacity=".13">
            <circle cx="300" cy="166" r="118" />
            <circle cx="300" cy="166" r="150" strokeDasharray="2 10" className="orbit-ring" />
          </g>
          <g fill="none" stroke="url(#network-line)" strokeWidth="1.5" strokeOpacity=".55">
            <path d="M95 168 H248" />
            <path d="M350 168 H505" />
            <path d="M95 168 C175 168 168 60 230 60 H340 Q390 60 390 105 V132 Q390 168 455 168 H505" />
            <path d="M95 168 C168 168 166 270 232 270 H345 Q404 270 404 226 V206 Q404 168 455 168 H505" />
          </g>
          <g className="network-packets" fill="#a5f3fc">
            <circle r="4"><animateMotion dur="3s" repeatCount="indefinite" path="M95 168 H248" /></circle>
            <circle r="4" fill="#d8b4fe"><animateMotion dur="3s" begin="1s" repeatCount="indefinite" path="M350 168 H505" /></circle>
            <circle r="3"><animateMotion dur="6s" repeatCount="indefinite" path="M95 168 C175 168 168 60 230 60 H340 Q390 60 390 105 V132 Q390 168 455 168 H505" /></circle>
            <circle r="3" fill="#e9a8ff"><animateMotion dur="7s" begin="1s" repeatCount="indefinite" path="M95 168 C168 168 166 270 232 270 H345 Q404 270 404 226 V206 Q404 168 455 168 H505" /></circle>
          </g>
          <g className="core-pulse"><circle cx="300" cy="166" r="61" fill="none" stroke="#a78bfa" strokeOpacity=".35" /></g>
          <rect x="252" y="118" width="96" height="96" rx="28" fill="#262048" stroke="#bda3ff" strokeWidth="1.5" />
          <path d="M300 141 L321 153 V178 L300 190 L279 178 V153 Z M300 141 V166 M279 153 L300 166 L321 153 M300 166 V190" fill="none" stroke="#e1d5ff" strokeWidth="2" strokeLinejoin="round" />
          <rect x="63" y="136" width="64" height="64" rx="20" fill="#113448" stroke="#67e8f9" />
          <path d="M82 162 H108 V179 H82 Z M82 162 V156 H104 M101 168 H110 V174 H101" fill="none" stroke="#a5f3fc" strokeWidth="2" strokeLinejoin="round" />
          <rect x="473" y="136" width="64" height="64" rx="20" fill="#302344" stroke="#d8b4fe" />
          <path d="M491 161 L505 153 L519 161 Z M494 165 V179 M505 165 V179 M516 165 V179 M490 183 H520" fill="none" stroke="#e9d5ff" strokeWidth="2" strokeLinejoin="round" />
          <g fill="#20233e" stroke="#a78bfa"><circle cx="230" cy="60" r="8" /><circle cx="390" cy="105" r="8" /><circle cx="232" cy="270" r="8" /><circle cx="404" cy="226" r="8" /></g>
          <g fill="#b7bdd9" fontFamily="Segoe UI, sans-serif" fontSize="11" textAnchor="middle"><text x="95" y="224">Subject wallet</text><text x="300" y="240" fill="#ddd0ff">Evidence engine</text><text x="505" y="224">Exchange</text><text x="300" y="40" fontSize="9" letterSpacing="2">TRACE EVERY CONNECTION</text></g>
        </svg>
      </div>
      <div className="relative z-10 mx-5 mb-5 grid grid-cols-3 gap-2 border-t border-soft-border pt-5 sm:mx-7 sm:mb-7">
        {[{ icon: Fingerprint, label: "Attribute", color: "text-primary" }, { icon: Layers3, label: "Explain", color: "text-info-text" }, { icon: ShieldCheck, label: "Assess risk", color: "text-good-text" }].map(({ icon: Icon, label, color }) => (
          <div key={label} className="flex flex-col gap-2 rounded-xl bg-white/[.025] p-3"><Icon size={18} className={color} /><span className="flex items-center justify-between text-[11px] text-body">{label}<ArrowUpRight size={12} className="text-muted" /></span></div>
        ))}
      </div>
    </div>
  );
}
