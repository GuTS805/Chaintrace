// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// End-to-end verification against ledger state produced by the real compiled
// contract (local simulator), including the on-chain code check.

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { ContractOperation, ContractState } from "@midnight-ntwrk/compact-runtime";
import { checkBundle, createBundle } from "../src/bundle.js";
import { fromHex } from "../src/hex.js";
import { CIRCUITS, type VerifierKeys, readConfirmedLedger, toConfirmedLedger } from "../src/ledger-read.js";
import { verdict } from "../src/verify.js";
import { PrivateCaseSimulator } from "./simulator.js";

const keys = Object.fromEntries(
  CIRCUITS.map((c) => [c, new Uint8Array(readFileSync(new URL(`../managed/private_case/keys/${c}.verifier`, import.meta.url)))]),
) as VerifierKeys;

const OWNER = new Uint8Array(32).fill(7);
const ADDRESS = "0".repeat(64);
const caseV1 = { id: 7, title: "Case", findings: [{ id: 1, note: "a" }] };
const caseV2 = { ...caseV1, findings: [...caseV1.findings, { id: 2, note: "b" }] };

/** Builds a ContractState like the one the indexer returns after deployment. */
function chainState(sim: PrivateCaseSimulator, verifierKeys: VerifierKeys = keys): ContractState {
  const state = new ContractState();
  state.data = sim.context.currentQueryContext.state;
  for (const circuit of CIRCUITS) {
    const op = new ContractOperation();
    op.verifierKey = verifierKeys[circuit];
    state.setOperation(circuit, op);
  }
  return state;
}

async function attested(...cases: (typeof caseV1)[]) {
  const sim = new PrivateCaseSimulator(OWNER);
  const bundles = [];
  for (const [i, c] of cases.entries()) {
    const bundle = await createBundle(c);
    sim.attest(BigInt(i), fromHex(bundle.commitment));
    bundles.push(bundle);
  }
  return { sim, bundles };
}

describe("reviewer verification", () => {
  it("verifies a bundle against the confirmed commitment", async () => {
    const { sim, bundles } = await attested(caseV1);
    const ledger = toConfirmedLedger(ADDRESS, chainState(sim), keys);
    const result = verdict(await checkBundle(bundles[0]), ledger, 1n);
    expect(result).toMatchObject({ status: "verified", revision: 1n });
  });

  it("reads through a PublicDataProvider and reports a missing contract", async () => {
    const { sim, bundles } = await attested(caseV1);
    const provider = { queryContractState: async (a: string) => (a === ADDRESS ? chainState(sim) : null) };
    const ok = await readConfirmedLedger(provider as never, ADDRESS, keys);
    expect(verdict(await checkBundle(bundles[0]), ok).status).toBe("verified");
    const missing = await readConfirmedLedger(provider as never, "f".repeat(64), keys);
    expect(verdict(await checkBundle(bundles[0]), missing)).toMatchObject({ reason: "contract-not-found" });
  });

  it("fails for a wrong salt", async () => {
    const { sim, bundles } = await attested(caseV1);
    const check = await checkBundle({ ...bundles[0], salt: "33".repeat(32) });
    expect(verdict(check, toConfirmedLedger(ADDRESS, chainState(sim), keys))).toMatchObject({ reason: "bundle-invalid" });
  });

  it("fails for a modified case even if the bundle commitment is recomputed", async () => {
    const { sim, bundles } = await attested(caseV1);
    const forged = await createBundle({ ...caseV1, title: "Edited" }, bundles[0].salt);
    expect(verdict(await checkBundle(forged), toConfirmedLedger(ADDRESS, chainState(sim), keys))).toMatchObject({
      reason: "commitment-mismatch",
    });
  });

  it("fails for the wrong contract (another case)", async () => {
    const { bundles } = await attested(caseV1);
    const other = await attested(caseV2);
    expect(
      verdict(await checkBundle(bundles[0]), toConfirmedLedger(ADDRESS, chainState(other.sim), keys)),
    ).toMatchObject({ reason: "commitment-mismatch" });
  });

  it("fails for a contract running different code", async () => {
    const { sim, bundles } = await attested(caseV1);
    // A real verifier key, but for the wrong circuit: models a look-alike contract
    // whose `attest` does not enforce the same rules.
    const fakeKeys = { ...keys, attest: keys.rotate_owner };
    const ledger = toConfirmedLedger(ADDRESS, chainState(sim, fakeKeys), keys);
    expect(verdict(await checkBundle(bundles[0]), ledger)).toMatchObject({ reason: "contract-code-mismatch" });
  });

  it("fails for a stale revision that was superseded", async () => {
    const { sim, bundles } = await attested(caseV1, caseV2);
    const ledger = toConfirmedLedger(ADDRESS, chainState(sim), keys);
    expect(verdict(await checkBundle(bundles[0]), ledger, 1n)).toMatchObject({ reason: "superseded" });
    expect(verdict(await checkBundle(bundles[1]), ledger, 2n).status).toBe("verified");
    expect(verdict(await checkBundle(bundles[1]), ledger, 1n)).toMatchObject({ reason: "revision-mismatch" });
  });

  it("fails before the first attestation", async () => {
    const sim = new PrivateCaseSimulator(OWNER);
    const bundle = await createBundle(caseV1);
    expect(verdict(await checkBundle(bundle), toConfirmedLedger(ADDRESS, chainState(sim), keys))).toMatchObject({
      reason: "not-attested",
    });
  });
});
