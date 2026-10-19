// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Private case attestation bundle: case snapshot + random 32-byte salt +
// commitment = SHA-256(canonicalJson({ domain, salt, case })).
// Must stay byte-for-byte compatible with midnight/src/bundle.ts; the Midnight
// test suite (midnight/test/bundle.test.ts) checks both against shared vectors.
import type { CaseDetail } from "@/lib/types";

export const ATTESTATION_FORMAT = "chaintrace-case-attestation-v1";

export interface CaseAttestationBundle {
  format: typeof ATTESTATION_FORMAT;
  case: CaseDetail;
  salt: string;
  commitment: string;
  created_at: string;
}

function hex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function canonicalJson(value: unknown): string {
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

function canonicalCase(caseDetail: CaseDetail): CaseDetail {
  if (!Array.isArray(caseDetail.findings)) return { ...caseDetail };
  return {
    ...caseDetail,
    findings: [...caseDetail.findings].sort((a, b) => {
      const ka = findingKey(a);
      const kb = findingKey(b);
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    }),
  };
}

export async function computeCaseCommitment(caseDetail: CaseDetail, salt: string): Promise<string> {
  const input = new TextEncoder().encode(
    canonicalJson({ domain: ATTESTATION_FORMAT, salt, case: canonicalCase(caseDetail) }),
  );
  return hex(new Uint8Array(await crypto.subtle.digest("SHA-256", input)));
}

export async function createCaseAttestation(caseDetail: CaseDetail): Promise<CaseAttestationBundle> {
  const salt = hex(crypto.getRandomValues(new Uint8Array(32)));
  const ordered = canonicalCase(caseDetail);
  return {
    format: ATTESTATION_FORMAT,
    case: ordered,
    salt,
    commitment: await computeCaseCommitment(ordered, salt),
    created_at: new Date().toISOString(),
  };
}
