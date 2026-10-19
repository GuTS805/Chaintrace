// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Case attestation bundle: a case snapshot, a random 32-byte salt and
// commitment = SHA-256(canonicalJson({ domain, salt, case })).
//
// Must stay byte-for-byte compatible with frontend/lib/case-attestation.ts;
// test/bundle.test.ts checks both implementations against the same vectors.

import { isHex32, randomBytes, toHex } from "./hex.js";

export const BUNDLE_FORMAT = "chaintrace-case-attestation-v1";

export type CaseSnapshot = { id: number | string; findings?: unknown[] } & Record<string, unknown>;

export interface CaseAttestationBundle {
  format: typeof BUNDLE_FORMAT;
  case: CaseSnapshot;
  salt: string;
  commitment: string;
  created_at: string;
}

export type BundleCheck =
  | { ok: true; bundle: CaseAttestationBundle; commitment: string }
  | { ok: false; reason: string };

/** JSON with object keys sorted at every level and no whitespace. */
export function canonicalJson(value: unknown): string {
  if (value === null) return "null";
  switch (typeof value) {
    case "boolean":
      return value ? "true" : "false";
    case "number":
      if (!Number.isFinite(value)) throw new Error("Non-finite number in case snapshot");
      return JSON.stringify(value);
    case "string":
      return JSON.stringify(value);
    case "object": {
      if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
      const entries = Object.entries(value as Record<string, unknown>)
        .filter(([, v]) => v !== undefined)
        .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
      return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`).join(",")}}`;
    }
    default:
      throw new Error(`Unsupported value in case snapshot: ${typeof value}`);
  }
}

function findingKey(finding: unknown): string {
  const id = (finding as { id?: unknown } | null)?.id;
  return typeof id === "number" ? id.toString().padStart(20, "0") : String(id);
}

/** Copy of the case with findings in stable id order. */
export function canonicalCase<T extends CaseSnapshot>(snapshot: T): T {
  if (!Array.isArray(snapshot.findings)) return { ...snapshot };
  return {
    ...snapshot,
    findings: [...snapshot.findings].sort((a, b) => {
      const ka = findingKey(a);
      const kb = findingKey(b);
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    }),
  };
}

export async function computeCommitment(snapshot: CaseSnapshot, salt: string): Promise<string> {
  if (!isHex32(salt)) throw new Error("Salt must be 32 bytes of lowercase hex");
  const input = new TextEncoder().encode(
    canonicalJson({ domain: BUNDLE_FORMAT, salt, case: canonicalCase(snapshot) }),
  );
  return toHex(new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", input)));
}

export async function createBundle(
  snapshot: CaseSnapshot,
  salt: string = toHex(randomBytes(32)),
  now: Date = new Date(),
): Promise<CaseAttestationBundle> {
  const ordered = canonicalCase(snapshot);
  return {
    format: BUNDLE_FORMAT,
    case: ordered,
    salt,
    commitment: await computeCommitment(ordered, salt),
    created_at: now.toISOString(),
  };
}

/** Validates structure and recomputes the commitment. Says nothing about the chain. */
export async function checkBundle(input: unknown): Promise<BundleCheck> {
  if (typeof input !== "object" || input === null) return { ok: false, reason: "Bundle is not a JSON object" };
  const b = input as Partial<CaseAttestationBundle>;
  if (b.format !== BUNDLE_FORMAT) return { ok: false, reason: `Unsupported bundle format: ${String(b.format)}` };
  if (!isHex32(b.salt)) return { ok: false, reason: "Salt must be 64 lowercase hex characters" };
  if (!isHex32(b.commitment)) return { ok: false, reason: "Commitment must be 64 lowercase hex characters" };
  if (typeof b.case !== "object" || b.case === null || Array.isArray(b.case)) {
    return { ok: false, reason: "Bundle has no case snapshot" };
  }
  let recomputed: string;
  try {
    recomputed = await computeCommitment(b.case, b.salt);
  } catch (err) {
    return { ok: false, reason: `Case snapshot cannot be hashed: ${(err as Error).message}` };
  }
  if (recomputed !== b.commitment) {
    return { ok: false, reason: "Case snapshot or salt does not match the bundle's commitment" };
  }
  return { ok: true, bundle: b as CaseAttestationBundle, commitment: recomputed };
}

export async function parseBundleFile(text: string): Promise<BundleCheck> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ok: false, reason: "File is not valid JSON" };
  }
  return checkBundle(parsed);
}
