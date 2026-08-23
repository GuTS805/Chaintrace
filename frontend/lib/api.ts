import type {
  AttributionResult,
  CaseDetail,
  CaseOut,
  Finding,
  GraphResult,
  RiskResult,
} from "./types";

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
