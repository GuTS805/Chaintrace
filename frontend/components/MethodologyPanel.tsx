import type { Methodology } from "@/lib/types";
import { fmtTime, pct } from "@/lib/format";
import { Panel, Pill } from "./ui";

function Row({ k, v, mono = false }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex gap-3 py-1.5">
      <span className="w-32 shrink-0 text-[10px] uppercase tracking-wider text-muted">
        {k}
      </span>
      <span className={`break-all text-[13px] text-text ${mono ? "tabular-nums" : ""}`}>
        {v}
      </span>
    </div>
  );
}

/**
 * Provenance for a completed investigation: which model and data source produced
 * the conclusion, how the traversal was bounded, and the hash that seals the
 * evidence. This is the part a reviewer cross-examines, so it is shown alongside
 * the verdict rather than buried in the PDF.
 */
export function MethodologyPanel({
  method,
  investigationId,
  chain,
}: {
  method: Methodology;
  investigationId: string;
  chain: string;
}) {
  const bounds = method.traversal_bounds as Record<string, unknown>;
  const boundsText = [
    `${bounds.max_hops ?? "?"} hops`,
    `${bounds.max_nodes ?? "?"} nodes`,
    `min value ${bounds.min_value_wei ?? "0"} wei`,
  ].join(" · ");

  return (
    <Panel
      title="Methodology & integrity"
      right={<Pill tone="vasp">{chain}</Pill>}
    >
      <div className="divide-y divide-border">
        <Row k="Investigation" v={investigationId} />
        <Row k="Model version" v={method.model_version} />
        <Row k="Data provider" v={method.provider} />
        <Row
          k="Threshold"
          v={pct(method.confidence_threshold, 0)}
          mono
        />
        <Row k="Traversal" v={boundsText} />
        <Row
          k="Data as of"
          v={method.data_timestamp ? fmtTime(method.data_timestamp) : "—"}
          mono
        />
        <Row k="Snapshot taken" v={fmtTime(method.snapshot_created_at)} mono />
      </div>

      <div className="mt-3 rounded border border-border bg-bg p-3">
        <div className="text-[10px] uppercase tracking-widest text-muted">
          evidence integrity hash · sha-256
        </div>
        <code className="mt-1 block break-all text-[11px] leading-relaxed text-good">
          {method.evidence_hash}
        </code>
        <p className="mt-2 text-[11px] leading-relaxed text-muted">
          Re-deriving this hash from the evidence records below must reproduce the
          same value. Any alteration to an observation changes it.
        </p>
      </div>
    </Panel>
  );
}
