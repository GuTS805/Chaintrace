import type { InvestigationStatus } from "@/lib/types";
import { INVESTIGATION_STAGES, STAGE_LABEL } from "@/lib/types";
import { Panel, Pill } from "./ui";

/**
 * Stage track for a running investigation.
 *
 * A traversal takes long enough that a bare spinner is not enough — an
 * investigator watching a slow case needs to know whether it is still pulling
 * chain data or already scoring candidates, so each stage is named.
 */
export function InvestigationProgress({
  status,
  error,
  startedAt,
  completedAt,
}: {
  status: InvestigationStatus;
  error?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
}) {
  const failed = status === "FAILED";
  // A failed run stops at whatever stage it reached; we do not know which, so
  // no stage is marked done rather than implying progress that may not have
  // happened.
  const currentIdx = failed ? -1 : INVESTIGATION_STAGES.indexOf(status);

  const elapsed =
    startedAt && completedAt
      ? `${(
          (new Date(completedAt).getTime() - new Date(startedAt).getTime()) /
          1000
        ).toFixed(1)}s`
      : null;

  return (
    <Panel
      title="Investigation progress"
      right={
        <div className="flex items-center gap-2">
          {elapsed && (
            <span className="text-[10px] tabular-nums text-muted">{elapsed}</span>
          )}
          <Pill tone={failed ? "bad" : status === "COMPLETED" ? "good" : "accent"}>
            {status}
          </Pill>
        </div>
      }
    >
      <ol className="space-y-2.5">
        {INVESTIGATION_STAGES.map((stage, i) => {
          const done = currentIdx > i;
          const active = currentIdx === i && status !== "COMPLETED";
          const isFinal = stage === "COMPLETED" && status === "COMPLETED";

          let mark = "○";
          let tone = "text-muted";
          if (done || isFinal) {
            mark = "✓";
            tone = "text-good";
          } else if (active) {
            mark = "●";
            tone = "text-accent";
          }

          return (
            <li key={stage} className="flex items-center gap-3">
              <span
                className={`w-3 text-center ${tone} ${
                  active ? "animate-pulse" : ""
                }`}
                aria-hidden
              >
                {mark}
              </span>
              <span
                className={`text-[13px] ${
                  done || isFinal || active ? "text-text" : "text-muted"
                }`}
              >
                {STAGE_LABEL[stage]}
              </span>
              {active && (
                <span className="text-[10px] uppercase tracking-widest text-accent">
                  running
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {failed && (
        <div className="mt-4 rounded border border-bad/40 bg-bad/5 p-3">
          <div className="text-[10px] uppercase tracking-widest text-bad">
            investigation failed
          </div>
          <p className="mt-1 break-words text-[13px] text-text">
            {error ?? "No reason was recorded."}
          </p>
        </div>
      )}
    </Panel>
  );
}
