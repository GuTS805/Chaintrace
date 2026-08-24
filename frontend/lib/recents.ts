"use client";

// Recent wallet lookups, kept client-side for the command palette — an
// investigator running many lookups a day benefits from jumping back into a
// recent trace without retyping the address (Elliptic/TRM design pattern:
// dense, repeat-use workflows need history, not just search).

const KEY = "chaintrace_recent_wallets";
const MAX = 8;

export interface RecentWallet {
  address: string;
  label?: string;
  at: number;
}

export function getRecents(): RecentWallet[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as RecentWallet[]) : [];
  } catch {
    return [];
  }
}

export function pushRecent(address: string, label?: string): void {
  try {
    const existing = getRecents().filter(
      (r) => r.address.toLowerCase() !== address.toLowerCase(),
    );
    const next = [{ address, label, at: Date.now() }, ...existing].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}
