import type {
  AttributionResult,
  CaseDetail,
  CaseOut,
  Finding,
  GraphResult,
  LiveTraceResult,
  RiskResult,
} from "./types";
import { clearSession, getToken, setSession, type StoredOfficer } from "./auth";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleUnauthorized(res: Response): Promise<void> {
  if (res.status === 401) {
    // Session expired or was never established — clear it so the auth guard
    // redirects to /login instead of retrying with a dead token forever.
    clearSession();
  }
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) {
    await handleUnauthorized(res);
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
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    await handleUnauthorized(res);
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} — ${detail.slice(0, 200)}`);
  }
  if (res.status === 204) return null;
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,
  login: async (username: string, password: string): Promise<StoredOfficer> => {
    const res = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(
        res.status === 401
          ? "Invalid username or password."
          : `${res.status} ${res.statusText} — ${detail.slice(0, 200)}`,
      );
    }
    const data = (await res.json()) as {
      access_token: string;
      officer: StoredOfficer;
    };
    setSession(data.access_token, data.officer);
    return data.officer;
  },
  logout: () => clearSession(),
  downloadPdf: async (path: string): Promise<{ blob: Blob; filename: string }> => {
    const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
    if (!res.ok) {
      await handleUnauthorized(res);
      const detail = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText} — ${detail.slice(0, 200)}`);
    }
    const disposition = res.headers.get("Content-Disposition") ?? "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    const filename = match ? match[1] : "report.pdf";
    const blob = await res.blob();
    return { blob, filename };
  },
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
  liveTrace: async (address: string): Promise<LiveTraceResult> => {
    const r = await sendJSON<LiveTraceResult>(
      `/wallets/${address}/live-trace`,
      "POST",
    );
    return r as LiveTraceResult;
  },
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
