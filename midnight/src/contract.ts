// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import { CompiledContract } from "@midnight-ntwrk/midnight-js-protocol/compact-js";
import type { MidnightProviders } from "@midnight-ntwrk/midnight-js-types";
import type { FoundContract } from "@midnight-ntwrk/midnight-js-contracts";
import * as PrivateCase from "../managed/private_case/contract/index.js";
import { type CasePrivateState, casePrivateStateId, witnesses } from "./witnesses.js";

export { PrivateCase };

export const CompiledPrivateCase = CompiledContract.make<PrivateCase.Contract<CasePrivateState>>(
  "ChaintracePrivateCase",
  PrivateCase.Contract<CasePrivateState>,
).pipe(CompiledContract.withWitnesses(witnesses), CompiledContract.withCompiledFileAssets("./managed/private_case"));

export type PrivateCaseContract = PrivateCase.Contract<CasePrivateState>;
export type PrivateCaseCircuit = Exclude<keyof PrivateCaseContract["provableCircuits"], number | symbol>;
export type PrivateCaseProviders = MidnightProviders<PrivateCaseCircuit, typeof casePrivateStateId, CasePrivateState>;
export type DeployedPrivateCase = FoundContract<PrivateCaseContract>;
