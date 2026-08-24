import type { RiskResult } from "@/lib/types";
import { shortAddr } from "@/lib/format";
import { Eyebrow, Pill, Tile } from "./ui";

const LEVEL_TONE: Record<string, "muted" | "warn" | "bad"> = {
  LOW: "muted",
  MEDIUM: "warn",
  HIGH: "bad",
  CRITICAL: "bad",
};

export function RiskPanel({
  risk,
  onHoverIndicator,
}: {
  risk: RiskResult;
  onHoverIndicator: (address: string | null) => void;
}) {
  const tone = LEVEL_TONE[risk.level] ?? "muted";
  const scoreTone = tone === "bad" ? "text-bad" : tone === "warn" ? "text-warn" : "text-text";

  return (
    <Tile bodyClassName="p-8">
      <div className="flex items-start justify-between gap-6">
        <Eyebrow>Risk</Eyebrow>
        {risk.flagged && <Pill tone="bad">Flagged</Pill>}
      </div>

      <div className="mt-3 flex items-end gap-4">
        <div className={`font-display text-[44px] font-semibold leading-none tabular-nums ${scoreTone}`}>
          {Math.round(risk.score * 100)}
        </div>
        <div className="pb-1 text-[13px] text-dim">/ 100</div>
        <div className="ml-auto pb-1 text-[15px] font-medium text-text">{risk.level}</div>
      </div>

      {risk.flagged && (
        <p className="mt-3 text-[13px] leading-relaxed text-muted">{risk.flag_reason}</p>
      )}

      {risk.typology_tags.length > 0 && (
        <div className="mt-5 flex flex-wrap gap-1.5">
          {risk.typology_tags.map((tag, i) => (
            <Pill key={i} tone="warn">
              {tag.category.replace("_", " ")}
            </Pill>
          ))}
        </div>
      )}

      <div className="mt-8 border-t border-border pt-6">
        <Eyebrow>Indicators</Eyebrow>
        <ul className="mt-3">
          {risk.indicators.length === 0 && (
            <li className="py-2 text-[13px] text-muted">
              No sanctioned / mixer / scam exposure detected.
            </li>
          )}
          {risk.indicators.slice(0, 6).map((ind, i) => (
            <li
              key={i}
              onMouseEnter={() => onHoverIndicator(ind.address)}
              onMouseLeave={() => onHoverIndicator(null)}
              className="-mx-2 flex items-start gap-3 rounded-md px-2 py-2 text-[13px] transition-colors hover:bg-panel2"
            >
              <Pill tone="bad" className="mt-0.5 shrink-0">
                {ind.category}
              </Pill>
              <span className="text-muted">
                {ind.description}{" "}
                <span className="font-mono text-[11px] text-dim">({shortAddr(ind.address)})</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-6 border-t border-border pt-4 text-[11px] text-dim">
        Computed independently of attribution
      </p>
    </Tile>
  );
}
