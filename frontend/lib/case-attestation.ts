// Copyright 2026 Chaintrace contributors. Licensed under Apache-2.0.
import type { CaseDetail } from "@/lib/types";

export interface CaseAttestationBundle {
  format: "chaintrace-case-attestation-v1";
  case: CaseDetail;
  salt: string;
  commitment: string;
  created_at: string;
}

function hex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function canonicalCase(caseDetail: CaseDetail): CaseDetail {
  return {
    ...caseDetail,
    findings: [...caseDetail.findings]
      .map((finding) => ({ ...finding }))
      .sort((a, b) => a.id - b.id),
  };
}

async function digest(caseDetail: CaseDetail, salt: string): Promise<string> {
  const input = new TextEncoder().encode(
    JSON.stringify({ domain: "chaintrace-case-attestation-v1", salt, case: canonicalCase(caseDetail) }),
  );
  return hex(new Uint8Array(await crypto.subtle.digest("SHA-256", input)));
}

export async function createCaseAttestation(caseDetail: CaseDetail): Promise<CaseAttestationBundle> {
  const salt = hex(crypto.getRandomValues(new Uint8Array(32)));
  return {
    format: "chaintrace-case-attestation-v1",
    case: canonicalCase(caseDetail),
    salt,
    commitment: await digest(caseDetail, salt),
    created_at: new Date().toISOString(),
  };
}

export async function verifyCaseAttestation(bundle: CaseAttestationBundle): Promise<boolean> {
  if (bundle.format !== "chaintrace-case-attestation-v1" || !/^[0-9a-f]{64}$/.test(bundle.salt)) {
    return false;
  }
  if (!/^[0-9a-f]{64}$/.test(bundle.commitment)) return false;
  return (await digest(bundle.case, bundle.salt)) === bundle.commitment;
}
