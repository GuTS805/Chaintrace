// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import type { PublicDataProvider } from "@midnight-ntwrk/midnight-js-types";
import { ledger } from "../managed/private_case/contract/index.js";
import { bytesEqual, toHex } from "./hex.js";
import type { ConfirmedLedger } from "./verify.js";

export const CIRCUITS = ["attest", "rotate_owner"] as const;

/** Verifier keys of this build, keyed by circuit name. */
export type VerifierKeys = Record<(typeof CIRCUITS)[number], Uint8Array>;

interface ContractStateLike {
  data: unknown;
  operation(name: string): { verifierKey: Uint8Array } | undefined;
  operations(): Array<string | Uint8Array>;
}

export function codeMatches(state: ContractStateLike, expected: VerifierKeys): boolean {
  const names = state.operations().map((op) => (typeof op === "string" ? op : new TextDecoder().decode(op)));
  if (names.length !== CIRCUITS.length || !CIRCUITS.every((c) => names.includes(c))) return false;
  return CIRCUITS.every((circuit) => {
    const op = state.operation(circuit);
    return !!op && bytesEqual(op.verifierKey, expected[circuit]);
  });
}

export function toConfirmedLedger(
  contractAddress: string,
  state: ContractStateLike,
  expected: VerifierKeys,
): ConfirmedLedger {
  const matches = codeMatches(state, expected);
  if (!matches) {
    return { contractAddress, caseCommitment: "", revision: 0n, codeMatches: false };
  }
  const l = ledger(state.data as Parameters<typeof ledger>[0]);
  return { contractAddress, caseCommitment: toHex(l.case_commitment), revision: l.revision, codeMatches: true };
}

/** Reads the latest contract state the indexer has from included blocks. */
export async function readConfirmedLedger(
  publicData: Pick<PublicDataProvider, "queryContractState">,
  contractAddress: string,
  expected: VerifierKeys,
): Promise<ConfirmedLedger | null> {
  const state = await publicData.queryContractState(contractAddress);
  if (!state) return null;
  return toConfirmedLedger(contractAddress, state as unknown as ContractStateLike, expected);
}

export async function fetchVerifierKeys(baseUrl: string, fetchFn: typeof fetch = fetch): Promise<VerifierKeys> {
  const entries = await Promise.all(
    CIRCUITS.map(async (circuit) => {
      const res = await fetchFn(`${baseUrl.replace(/\/$/, "")}/keys/${circuit}.verifier`);
      if (!res.ok) throw new Error(`Could not load verifier key for ${circuit}: HTTP ${res.status}`);
      return [circuit, new Uint8Array(await res.arrayBuffer())] as const;
    }),
  );
  return Object.fromEntries(entries) as VerifierKeys;
}
