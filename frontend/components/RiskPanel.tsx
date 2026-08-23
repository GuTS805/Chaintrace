import type { RiskResult } from "@/lib/types";
import { pct, shortAddr } from "@/lib/format";
import { Bar, Panel, Pill } from "./ui";

const LEVEL_TONE: Record<string, "muted" | "warn" | "bad"> = {
  LOW: "muted",
  MEDIUM: "warn",
  HIGH: "bad",
  CRITICAL: "bad",
};

export function RiskPanel({ risk }: { risk: RiskResult }) {
  const tone = LEVEL_TONE[risk.level] ?? "muted";
  return (
    <Panel title="Risk" right={<Pill tone={tone}>{risk.level}</Pill>}>
      <div className="mb-1 flex items-center justify-between text-xs text-muted">
        <span>exposure score</span>
        <span className="tabular-nums">{pct(risk.score, 0)}</span>
      </div>
      <Bar value={risk.score} tone={tone === "muted" ? "accent" : tone} />

      <ul className="mt-3 space-y-1.5">
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
      <p className="mt-3 text-[10px] text-muted">
        Risk is computed independently of VASP attribution.
      </p>
    </Panel>
  );
}
