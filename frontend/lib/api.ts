import type {
  AttributionResult,
  CaseDetail,
  CaseOut,
  EvidenceBundle,
  Finding,
  GraphResult,
  InvestigationCreate,
  InvestigationDetail,
  InvestigationGraph,
  InvestigationOut,
  RiskResult,
} from "./types";
import { isTerminal } from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} — ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

async function sendJSON<T>(
  path: string,
  method: "POST" | "DELETE",
  body?: unknown,
): Promise<T | null> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} — ${detail.slice(0, 200)}`);
  }
  if (res.status === 204) return null;
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,

  // --- investigations (primary resource) ---
  /** Open an investigation. Returns as soon as the job is accepted (202). */
  createInvestigation: (body: InvestigationCreate) =>
    sendJSON<InvestigationOut>(`/investigations`, "POST", body),
  getInvestigation: (id: string) =>
    getJSON<InvestigationDetail>(`/investigations/${id}`),
  listInvestigations: (caseId?: number) =>
    getJSON<InvestigationOut[]>(
      caseId === undefined ? `/investigations` : `/investigations?case_id=${caseId}`,
    ),
  investigationGraph: (id: string) =>
    getJSON<InvestigationGraph>(`/investigations/${id}/graph`),
  investigationAttribution: (id: string) =>
    getJSON<AttributionResult>(`/investigations/${id}/attribution`),
  investigationRisk: (id: string) =>
    getJSON<RiskResult>(`/investigations/${id}/risk`),
  investigationEvidence: (id: string) =>
    getJSON<EvidenceBundle>(`/investigations/${id}/evidence`),
  investigationReportUrl: (id: string) => `${BASE}/investigations/${id}/report`,

  // --- ad-hoc wallet lookups (no durable record) ---
  attribution: (address: string, depth = 6) =>
    getJSON<AttributionResult>(
      `/wallets/${address}/attribution?depth=${depth}`,
    ),
  risk: (address: string, depth = 6) =>
    getJSON<RiskResult>(`/wallets/${address}/risk?depth=${depth}`),
  graph: (address: string, depth = 4, direction = "FORWARD") =>
    getJSON<GraphResult>(
      `/wallets/${address}/graph?depth=${depth}&direction=${direction}`,
    ),
  listCases: () => getJSON<CaseOut[]>(`/cases`),
  getCase: (id: number) => getJSON<CaseDetail>(`/cases/${id}`),
  createCase: (body: {
    name: string;
    description?: string;
    investigator?: string;
  }) => sendJSON<CaseOut>(`/cases`, "POST", body),
  deleteCase: (id: number) => sendJSON<null>(`/cases/${id}`, "DELETE"),
  addFinding: (
    caseId: number,
    body: {
      title: string;
      description?: string;
      severity?: string;
      wallet_address?: string;
      evidence?: Record<string, unknown>;
    },
  ) => sendJSON<Finding>(`/cases/${caseId}/findings`, "POST", body),
};

/**
 * Poll an investigation until it finishes, reporting each stage change.
 *
 * Resolves on COMPLETED *or* FAILED — a failed investigation is a real outcome
 * the caller must render, not an exception. Rejects only if the run outlasts
 * `timeoutMs`, so a hung job cannot leave the UI spinning forever.
 */
export async function pollInvestigation(
  id: string,
  onStage?: (inv: InvestigationDetail) => void,
  { intervalMs = 1000, timeoutMs = 300_000 }: PollOptions = {},
): Promise<InvestigationDetail> {
  const deadline = Date.now() + timeoutMs;
  let lastStatus = "";

  for (;;) {
    const inv = await api.getInvestigation(id);
    if (inv.status !== lastStatus) {
      lastStatus = inv.status;
      onStage?.(inv);
    }
    if (isTerminal(inv.status)) return inv;
    if (Date.now() >= deadline) {
      throw new Error(
        `Investigation ${id} did not finish within ${Math.round(
          timeoutMs / 1000,
        )}s (last stage: ${inv.status}).`,
      );
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export interface PollOptions {
  intervalMs?: number;
  timeoutMs?: number;
}
