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

export interface LiveTraceResult {
  address: string;
  imported_transactions: number;
  total_transactions: number;
  source: "cache" | "blockscout";
}
