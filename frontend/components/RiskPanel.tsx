import type { RiskResult } from "@/lib/types";
import { pct, shortAddr } from "@/lib/format";
import { Panel, Pill } from "./ui";

const LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
const LEVEL_TONE: Record<string, "muted" | "warn" | "bad"> = {
  LOW: "muted",
  MEDIUM: "warn",
  HIGH: "bad",
  CRITICAL: "bad",
};
const FILL: Record<string, string> = {
  muted: "bg-muted",
  warn: "bg-warn",
  bad: "bg-bad",
};

export function RiskPanel({ risk }: { risk: RiskResult }) {
  const tone = LEVEL_TONE[risk.level] ?? "muted";
  const activeIdx = LEVELS.indexOf(risk.level as (typeof LEVELS)[number]);

  return (
    <Panel title="Risk" right={<Pill tone={tone}>{risk.level}</Pill>}>
      {/* Stepped threat meter. */}
      <div className="flex items-center gap-3">
        <div className="flex flex-1 gap-1">
          {LEVELS.map((lvl, i) => (
            <div key={lvl} className="flex-1">
              <div
                className={`h-1.5 rounded-full ${
                  i <= activeIdx ? FILL[tone] : "bg-panel2"
                }`}
              />
              <div className="mt-1 text-center text-[9px] uppercase tracking-wider text-muted">
                {lvl.slice(0, 4)}
              </div>
            </div>
          ))}
        </div>
        <span className={`font-display text-xl tabular-nums text-${tone}`}>
          {pct(risk.score, 0)}
        </span>
      </div>

      <ul className="mt-4 space-y-1.5">
        {risk.indicators.length === 0 && (
          <li className="text-xs text-muted">
            No sanctioned / mixer / scam exposure detected.
          </li>
        )}
        {risk.indicators.slice(0, 6).map((ind, i) => (
          <li key={i} className="flex items-start gap-2 text-xs">
            <Pill tone="bad">{ind.category}</Pill>
            <span className="flex-1 text-text">
              {ind.description}{" "}
              <span className="text-muted">({shortAddr(ind.address)})</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 border-t border-border pt-2 text-[10px] uppercase tracking-widest text-muted">
        computed independently of attribution
      </p>
    </Panel>
  );
}
