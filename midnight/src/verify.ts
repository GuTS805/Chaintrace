// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Reviewer verdict: a bundle verifies only when it is internally consistent AND
// its commitment equals the latest commitment read from the confirmed ledger
// state of a contract running this exact code.

import type { BundleCheck } from "./bundle.js";

export interface ConfirmedLedger {
  contractAddress: string;
  /** Hex of the on-chain case_commitment. */
  caseCommitment: string;
  revision: bigint;
  /** True when every circuit's on-chain verifier key equals this build's key. */
  codeMatches: boolean;
}

export type VerifyFailure =
  | "bundle-invalid"
  | "contract-not-found"
  | "contract-code-mismatch"
  | "not-attested"
  | "superseded"
  | "commitment-mismatch"
  | "revision-mismatch";

export type Verdict =
  | { status: "verified"; commitment: string; revision: bigint; contractAddress: string }
  | { status: "failed"; reason: VerifyFailure; message: string };

const fail = (reason: VerifyFailure, message: string): Verdict => ({ status: "failed", reason, message });

/**
 * @param expectedRevision Revision the investigator claims for this bundle
 *   (from the attestation receipt). Optional.
 */
export function verdict(bundle: BundleCheck, ledger: ConfirmedLedger | null, expectedRevision?: bigint): Verdict {
  if (!bundle.ok) return fail("bundle-invalid", bundle.reason);
  if (!ledger) return fail("contract-not-found", "No confirmed contract state at this address on this network");
  if (!ledger.codeMatches) {
    return fail("contract-code-mismatch", "The contract at this address is not the Chaintrace private case contract");
  }
  if (ledger.revision === 0n) return fail("not-attested", "This case contract has no attestation yet");

  if (bundle.commitment !== ledger.caseCommitment) {
    if (expectedRevision !== undefined && expectedRevision < ledger.revision) {
      return fail(
        "superseded",
        `Bundle claims revision ${expectedRevision}, but the case is now at revision ${ledger.revision}. ` +
          "Only the latest revision can be verified against the chain.",
      );
    }
    return fail("commitment-mismatch", "Bundle commitment differs from the confirmed on-chain commitment");
  }
  if (expectedRevision !== undefined && expectedRevision !== ledger.revision) {
    return fail(
      "revision-mismatch",
      `Commitment matches revision ${ledger.revision}, but the receipt claims revision ${expectedRevision}`,
    );
  }
  return {
    status: "verified",
    commitment: ledger.caseCommitment,
    revision: ledger.revision,
    contractAddress: ledger.contractAddress,
  };
}
