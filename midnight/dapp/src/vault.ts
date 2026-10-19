// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { type KeyValueStore, SecretVault, memoryStore } from "../../src/secret-vault.js";

function browserStore(): KeyValueStore {
  try {
    const probe = "chaintrace:probe";
    window.localStorage.setItem(probe, "1");
    window.localStorage.removeItem(probe);
    return window.localStorage;
  } catch {
    return memoryStore();
  }
}

export const vault = new SecretVault(browserStore());

const CONTRACT_KEY = "chaintrace:case-contract";

/** Remembers which contract this browser used for a case. Local convenience only. */
export function rememberContract(network: string, caseId: string | number, address: string) {
  try {
    window.localStorage.setItem(`${CONTRACT_KEY}:${network}:${caseId}`, address);
  } catch {
    /* storage unavailable */
  }
}

export function recallContract(network: string, caseId: string | number): string | null {
  try {
    return window.localStorage.getItem(`${CONTRACT_KEY}:${network}:${caseId}`);
  } catch {
    return null;
  }
}
