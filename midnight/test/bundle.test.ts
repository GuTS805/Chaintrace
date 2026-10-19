// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { canonicalJson, checkBundle, computeCommitment, createBundle, parseBundleFile } from "../src/bundle.js";
import * as frontend from "../../frontend/lib/case-attestation.js";
import vector from "./vectors/bundle-v1.json" with { type: "json" };

const SALT = "11".repeat(32);

const sampleCase = {
  id: 42,
  title: "Mixer outflow review",
  status: "OPEN",
  investigator: "officer-17",
  created_at: "2026-10-01T10:00:00Z",
  findings: [
    { id: 9, severity: "HIGH", note: "Peel chain to exchange", address: "0xabc" },
    { id: 3, severity: "INFO", note: "First seen", address: "0xdef" },
  ],
};

describe("canonical JSON", () => {
  it("sorts keys at every level and drops undefined", () => {
    expect(canonicalJson({ b: 1, a: { d: [2, { z: 1, y: undefined, x: "é" }], c: null } })).toBe(
      '{"a":{"c":null,"d":[2,{"x":"é","z":1}]},"b":1}',
    );
  });

  it("rejects values JSON cannot represent faithfully", () => {
    expect(() => canonicalJson({ n: Number.NaN })).toThrow(/Non-finite/);
    expect(() => canonicalJson({ f: () => 1 })).toThrow(/Unsupported/);
  });
});

describe("case bundle", () => {
  it("matches the published test vector", async () => {
    expect(await computeCommitment(vector.case, vector.salt)).toBe(vector.commitment);
    expect((await checkBundle(vector)).ok).toBe(true);
  });

  it("is independent of key order and finding order", async () => {
    const reordered = {
      findings: [...sampleCase.findings].reverse().map((f) => ({ note: f.note, address: f.address, severity: f.severity, id: f.id })),
      created_at: sampleCase.created_at,
      investigator: sampleCase.investigator,
      status: sampleCase.status,
      title: sampleCase.title,
      id: sampleCase.id,
    };
    expect(await computeCommitment(reordered, SALT)).toBe(await computeCommitment(sampleCase, SALT));
  });

  it("produces the same commitment as the Chaintrace frontend helper", async () => {
    const a = await createBundle(sampleCase, SALT, new Date("2026-10-19T00:00:00Z"));
    const b = await frontend.computeCaseCommitment(sampleCase as never, SALT);
    expect(b).toBe(a.commitment);
    expect(await frontend.computeCaseCommitment(vector.case as never, vector.salt)).toBe(vector.commitment);
    const fromFrontend = await frontend.createCaseAttestation(sampleCase as never);
    expect((await checkBundle(JSON.parse(JSON.stringify(fromFrontend)))).ok).toBe(true);
  });

  it("generates a fresh 32-byte salt per bundle", async () => {
    const a = await createBundle(sampleCase);
    const b = await createBundle(sampleCase);
    expect(a.salt).toMatch(/^[0-9a-f]{64}$/);
    expect(a.salt).not.toBe(b.salt);
    expect(a.commitment).not.toBe(b.commitment);
  });

  it("survives a JSON file round trip", async () => {
    const bundle = await createBundle(sampleCase);
    const check = await parseBundleFile(JSON.stringify(bundle, null, 2));
    expect(check.ok && check.commitment).toBe(bundle.commitment);
  });

  it("fails with a wrong salt", async () => {
    const bundle = await createBundle(sampleCase);
    const check = await checkBundle({ ...bundle, salt: "22".repeat(32) });
    expect(check.ok).toBe(false);
  });

  it("fails when the case was modified", async () => {
    const bundle = await createBundle(sampleCase);
    const tampered = structuredClone(bundle);
    tampered.case.findings![0] = { ...(tampered.case.findings![0] as object), severity: "LOW" };
    expect((await checkBundle(tampered)).ok).toBe(false);
    expect((await checkBundle({ ...bundle, case: { ...bundle.case, status: "CLOSED" } })).ok).toBe(false);
  });

  it("rejects malformed input", async () => {
    expect((await parseBundleFile("not json")).ok).toBe(false);
    expect((await checkBundle(null)).ok).toBe(false);
    expect((await checkBundle({ format: "other" })).ok).toBe(false);
    const bundle = await createBundle(sampleCase);
    expect((await checkBundle({ ...bundle, commitment: bundle.commitment.toUpperCase() })).ok).toBe(false);
    expect((await checkBundle({ ...bundle, case: [] })).ok).toBe(false);
  });
});
