// Copyright 2026 Chaintrace contributors.
// Portions adapted from midnightntwrk/example-bboard, Copyright (C) Midnight Foundation.
// SPDX-License-Identifier: Apache-2.0
//
// In-memory PrivateStateProvider. Private state (the unlocked owner secret)
// lives only for the duration of one operation and is removed afterwards; the
// durable copy is the passphrase-sealed secret in src/secret-vault.ts.
// The contract maintenance signing key also stays in memory only, so after the
// page closes nobody holds a key that could replace the contract's circuits.

import type { ContractAddress, SigningKey } from "@midnight-ntwrk/compact-runtime";
import type { PrivateStateId, PrivateStateProvider } from "@midnight-ntwrk/midnight-js-types";

export function inMemoryPrivateStateProvider<PSI extends PrivateStateId, PS>(): PrivateStateProvider<PSI, PS> {
  const states = new Map<ContractAddress, Map<PSI, PS>>();
  const signingKeys = new Map<ContractAddress, SigningKey>();
  let address: ContractAddress | null = null;

  const scoped = (): Map<PSI, PS> => {
    if (address === null) throw new Error("Contract address not set for private state");
    let map = states.get(address);
    if (!map) states.set(address, (map = new Map()));
    return map;
  };
  const unsupported = () => Promise.reject(new Error("Private state export is disabled; back up the sealed owner secret instead"));

  return {
    setContractAddress(a) {
      address = a;
    },
    set: async (key, state) => void scoped().set(key, state),
    get: async (key) => scoped().get(key) ?? null,
    remove: async (key) => void scoped().delete(key),
    clear: async () => void (address !== null && states.delete(address)),
    setSigningKey: async (a, key) => void signingKeys.set(a, key),
    getSigningKey: async (a) => signingKeys.get(a) ?? null,
    removeSigningKey: async (a) => void signingKeys.delete(a),
    clearSigningKeys: async () => signingKeys.clear(),
    exportPrivateStates: unsupported,
    importPrivateStates: unsupported,
    exportSigningKeys: unsupported,
    importSigningKeys: unsupported,
  };
}
