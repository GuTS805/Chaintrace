// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Runs the compiled contract locally with the Compact runtime (no network, no proofs).

import {
  type CircuitContext,
  CostModel,
  QueryContext,
  createConstructorContext,
  sampleContractAddress,
} from "@midnight-ntwrk/compact-runtime";
import { Contract, type Ledger, ledger, pureCircuits } from "../managed/private_case/contract/index.js";
import { type CasePrivateState, witnesses } from "../src/witnesses.js";

export class PrivateCaseSimulator {
  readonly contract = new Contract<CasePrivateState>(witnesses);
  context: CircuitContext<CasePrivateState>;

  constructor(ownerSecret: Uint8Array) {
    const { currentPrivateState, currentContractState, currentZswapLocalState } = this.contract.initialState(
      createConstructorContext({ ownerSecret }, "0".repeat(64)),
    );
    this.context = {
      currentPrivateState,
      currentZswapLocalState,
      costModel: CostModel.initialCostModel(),
      currentQueryContext: new QueryContext(currentContractState.data, sampleContractAddress()),
    };
  }

  /** Simulates a different caller by swapping the local private state. */
  as(ownerSecret: Uint8Array): this {
    this.context = { ...this.context, currentPrivateState: { ownerSecret } };
    return this;
  }

  ledger(): Ledger {
    return ledger(this.context.currentQueryContext.state);
  }

  attest(expectedRevision: bigint, commitment: Uint8Array): Ledger {
    this.context = this.contract.impureCircuits.attest(this.context, expectedRevision, commitment).context;
    return this.ledger();
  }

  rotateOwner(newOwnerKey: Uint8Array): Ledger {
    this.context = this.contract.impureCircuits.rotate_owner(this.context, newOwnerKey).context;
    return this.ledger();
  }

  static ownerKey(secret: Uint8Array): Uint8Array {
    return pureCircuits.derive_owner_key(secret);
  }
}
