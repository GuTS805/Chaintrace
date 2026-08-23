// TypeScript mirrors of the backend Pydantic schemas.

export type SignalType =
  | "HOP_PATH"
  | "DEPOSIT_SWEEP"
  | "COUNTERPARTY_OVERLAP"
  | "TEMPORAL_CORRELATION"
  | "KNOWN_LABEL"
  | "PATTERN_SIMILARITY";

export interface Evidence {
  signal_type: SignalType;
  description: string;
  weight: number;
  tx_hashes: string[];
  timestamps: string[];
}

export interface VaspCandidate {
  vasp_name: string;
  probability: number;
  evidence: Evidence[];
  /** The labeled address actually reached, not just the brand it belongs to. */
  hot_wallet: string | null;
}

export interface AttributionResult {
  candidates: VaspCandidate[];
  insufficient_evidence: boolean;
  ambiguous: boolean;
  explanation: string | null;
  confidence_threshold: number;
  model_version: string;
}

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RiskIndicator {
  category: string;
  description: string;
  address: string;
  hops: number;
  contribution: number;
}

export interface RiskResult {
  wallet: string;
  score: number;
  level: RiskLevel;
  indicators: RiskIndicator[];
}

export interface GraphNode {
  address: string;
  depth: number;
  is_labeled: boolean;
  label_name: string | null;
  vasp_name: string | null;
  is_contract: boolean;
}

export interface GraphEdge {
  tx_hash: string;
  from_address: string;
  to_address: string;
  value_wei: string;
  timestamp: string;
}

export interface PruneInfo {
  pruned: boolean;
  reasons: string[];
  nodes_visited: number;
  max_depth_reached: number;
}

export interface GraphResult {
  root: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  prune: PruneInfo;
}

export type CaseStatus = "OPEN" | "IN_REVIEW" | "CLOSED";
export type FindingSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface CaseOut {
  id: number;
  name: string;
  description: string | null;
  status: CaseStatus;
  investigator: string | null;
  created_at: string;
}

export interface Finding {
  id: number;
  case_id: number;
  title: string;
  description: string | null;
  severity: FindingSeverity;
  wallet_address: string | null;
  evidence: Record<string, unknown> | null;
  created_at: string;
}

export interface CaseDetail extends CaseOut {
  findings: Finding[];
}

// --- Investigations: the primary resource ---------------------------------

export type Chain = "ethereum" | "bitcoin" | "polygon" | "arbitrum" | "base";

/**
 * Investigation lifecycle. The intermediate stages are surfaced deliberately: a
 * real traversal takes long enough that an investigator needs to see which phase
 * is running, not just a spinner.
 */
export type InvestigationStatus =
  | "QUEUED"
  | "FETCHING"
  | "TRAVERSING"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED";

/** Stages in the order a progress track should render them. */
export const INVESTIGATION_STAGES: InvestigationStatus[] = [
  "QUEUED",
  "FETCHING",
  "TRAVERSING",
  "ANALYZING",
  "COMPLETED",
];

export const STAGE_LABEL: Record<InvestigationStatus, string> = {
  QUEUED: "Queued",
  FETCHING: "Fetching chain data",
  TRAVERSING: "Building graph",
  ANALYZING: "Computing attribution & risk",
  COMPLETED: "Complete",
  FAILED: "Failed",
};

export function isTerminal(status: InvestigationStatus): boolean {
  return status === "COMPLETED" || status === "FAILED";
}

export interface InvestigationOut {
  id: string;
  chain: string;
  address: string;
  status: InvestigationStatus;
  depth: number;
  max_nodes: number;
  requested_by: string | null;
  case_id: number | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  has_result: boolean;
}

/** How a conclusion was produced — what makes the report defensible. */
export interface Methodology {
  model_version: string;
  provider: string;
  confidence_threshold: number;
  traversal_bounds: Record<string, unknown>;
  data_timestamp: string | null;
  evidence_hash: string;
  snapshot_created_at: string;
}

export interface InvestigationDetail extends InvestigationOut {
  attribution: AttributionResult | null;
  risk: RiskResult | null;
  methodology: Methodology | null;
}

export interface EvidenceRecord {
  evidence_id: string;
  investigation_id: string;
  chain: string;
  vasp_name: string;
  signal_type: SignalType;
  description: string;
  weight: number;
  source_transaction: string | null;
  source_wallet: string;
  target_wallet: string | null;
  observed_at: string | null;
  created_at: string;
  model_version: string;
  provider: string;
}

export interface EvidenceBundle {
  investigation_id: string;
  evidence_hash: string;
  record_count: number;
  records: EvidenceRecord[];
}

export interface InvestigationGraph {
  investigation_id: string;
  graph: GraphResult;
}

export interface InvestigationCreate {
  address: string;
  chain?: Chain;
  depth?: number;
  min_value_wei?: number;
  max_nodes?: number;
  case_id?: number;
  requested_by?: string;
}
