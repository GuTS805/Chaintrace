// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { PrivateCaseSimulator } from "./simulator.js";

const secret = (fill: number) => new Uint8Array(32).fill(fill);
const digest = (fill: number) => new Uint8Array(32).fill(fill);

const OWNER = secret(7);
const INTRUDER = secret(8);

describe("private_case contract", () => {
  it("deploys with no commitment, revision 0, and the owner's derived key", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    const state = sim.ledger();
    expect(state.revision).toBe(0n);
    expect(state.case_commitment).toEqual(new Uint8Array(32));
    expect(state.owner_key).toEqual(PrivateCaseSimulator.ownerKey(OWNER));
  });

  it("does not publish the owner secret", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    const state = sim.ledger();
    for (const value of [state.owner_key, state.case_commitment]) {
      expect(value).not.toEqual(OWNER);
    }
  });

  it("domain-separates the owner key from a plain hash of the secret", () => {
    expect(PrivateCaseSimulator.ownerKey(OWNER)).not.toEqual(PrivateCaseSimulator.ownerKey(INTRUDER));
    expect(PrivateCaseSimulator.ownerKey(OWNER)).toHaveLength(32);
  });

  it("lets the owner attest and then attest a later revision", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    let state = sim.attest(0n, digest(1));
    expect(state.case_commitment).toEqual(digest(1));
    expect(state.revision).toBe(1n);

    state = sim.attest(1n, digest(2));
    expect(state.case_commitment).toEqual(digest(2));
    expect(state.revision).toBe(2n);
  });

  it("rejects attestation from a caller without the owner secret", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    sim.attest(0n, digest(1));
    sim.as(INTRUDER);
    expect(() => sim.attest(1n, digest(3))).toThrow(/Unauthorized/);
    expect(sim.ledger().case_commitment).toEqual(digest(1));
    expect(sim.ledger().revision).toBe(1n);
  });

  it("rejects a call when the owner secret is not loaded", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    sim.context = { ...sim.context, currentPrivateState: {} as never };
    expect(() => sim.attest(0n, digest(1))).toThrow(/not unlocked/);
  });

  it("rejects a stale or replayed transaction built for an older revision", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    sim.attest(0n, digest(1));
    expect(() => sim.attest(0n, digest(2))).toThrow(/Stale revision/);
    expect(() => sim.attest(5n, digest(2))).toThrow(/Stale revision/);
    expect(sim.ledger().revision).toBe(1n);
  });

  it("rejects re-attesting the current commitment and the empty commitment", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    expect(() => sim.attest(0n, new Uint8Array(32))).toThrow(/Empty commitment/);
    sim.attest(0n, digest(1));
    expect(() => sim.attest(1n, digest(1))).toThrow(/already attested/);
  });

  it("rotates ownership: the new secret works, the old one stops working", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    sim.attest(0n, digest(1));
    const next = secret(9);
    const state = sim.rotateOwner(PrivateCaseSimulator.ownerKey(next));
    expect(state.owner_key).toEqual(PrivateCaseSimulator.ownerKey(next));
    expect(state.revision).toBe(1n);

    expect(() => sim.attest(1n, digest(2))).toThrow(/Unauthorized/);
    sim.as(next);
    expect(sim.attest(1n, digest(2)).revision).toBe(2n);
  });

  it("rejects rotation by a non-owner and rotation to the same key", () => {
    const sim = new PrivateCaseSimulator(OWNER);
    expect(() => sim.rotateOwner(PrivateCaseSimulator.ownerKey(OWNER))).toThrow(/equals current key/);
    sim.as(INTRUDER);
    expect(() => sim.rotateOwner(PrivateCaseSimulator.ownerKey(INTRUDER))).toThrow(/Unauthorized/);
    expect(sim.ledger().owner_key).toEqual(PrivateCaseSimulator.ownerKey(OWNER));
  });

  it("isolates deployments: one case's secret cannot update another case", () => {
    const caseA = new PrivateCaseSimulator(OWNER);
    const caseB = new PrivateCaseSimulator(INTRUDER);
    caseA.attest(0n, digest(1));
    caseB.as(OWNER);
    expect(() => caseB.attest(0n, digest(1))).toThrow(/Unauthorized/);
  });
});
