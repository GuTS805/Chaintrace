"use client";

export interface StoredOfficer {
  id: number;
  username: string;
  full_name: string;
  badge_no: string | null;
  department: string | null;
}

const TOKEN_KEY = "chaintrace_token";
const OFFICER_KEY = "chaintrace_officer";
const AUTH_EVENT = "chaintrace-auth-change";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getOfficer(): StoredOfficer | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(OFFICER_KEY);
    return raw ? (JSON.parse(raw) as StoredOfficer) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, officer: StoredOfficer): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(OFFICER_KEY, JSON.stringify(officer));
    window.dispatchEvent(new Event(AUTH_EVENT));
  } catch {
    // localStorage unavailable (private mode etc.) — session just won't persist.
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(OFFICER_KEY);
    window.dispatchEvent(new Event(AUTH_EVENT));
  } catch {
    // ignore
  }
}

export function onAuthChange(cb: () => void): () => void {
  window.addEventListener(AUTH_EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(AUTH_EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}
