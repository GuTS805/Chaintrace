// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import type { WitnessContext } from "@midnight-ntwrk/compact-runtime";
import type { Ledger } from "../managed/private_case/contract/index.js";

/** Local-only private state. Never logged, never sent anywhere but the local prover. */
export interface CasePrivateState {
  readonly ownerSecret: Uint8Array;
}

export const casePrivateStateId = "chaintracePrivateCase";

export const witnesses = {
  owner_secret: ({ privateState }: WitnessContext<Ledger, CasePrivateState>): [CasePrivateState, Uint8Array] => {
    if (!(privateState?.ownerSecret instanceof Uint8Array) || privateState.ownerSecret.length !== 32) {
      throw new Error("Owner secret is not unlocked");
    }
    return [privateState, privateState.ownerSecret];
  },
};
