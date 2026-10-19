// @vitest-environment jsdom
// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// DApp flow tests. The Midnight network layer (case-api) is mocked; these check
// what the UI claims at each step, e.g. that "Confirmed" never appears before
// the confirmed stage.

import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createBundle } from "../src/bundle.js";
import type { TxStage } from "../src/tx-stages.js";
import type { ConfirmedLedger } from "../src/verify.js";

Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });

const ADDRESS = "c0".repeat(32);
const ledgerState: { current: ConfirmedLedger | null } = { current: null };
const gate: { release?: () => void } = {};

vi.mock("../dapp/src/case-api.js", () => ({
  readOnlyPublicData: () => ({}),
  readCase: vi.fn(async () => ledgerState.current),
  buildProviders: vi.fn(() => ({})),
  primeWalletKeys: vi.fn(async () => {}),
  isReceipt: (r: { format?: string }) => r?.format === "chaintrace-attestation-receipt-v1",
  deployCase: vi.fn(async (_p: unknown, _s: Uint8Array, onStage: (s: TxStage) => void) => {
    onStage({ stage: "proving" });
    onStage({ stage: "submitted", txId: "deploy-tx" });
    onStage({ stage: "confirmed", txId: "deploy-tx", txHash: "aa".repeat(32), blockHeight: 10 });
    return { contractAddress: ADDRESS, ledger: { contractAddress: ADDRESS, caseCommitment: "", revision: 0n, codeMatches: true }, confirmation: {} };
  }),
  attestCase: vi.fn(async (_p: unknown, addr: string, _s: Uint8Array, commitment: string, onStage: (s: TxStage) => void) => {
    onStage({ stage: "proving" });
    onStage({ stage: "prepared" });
    onStage({ stage: "submitted", txId: "attest-tx" });
    await new Promise<void>((resolve) => (gate.release = resolve));
    onStage({ stage: "confirmed", txId: "attest-tx", txHash: "bb".repeat(32), blockHeight: 11 });
    const ledger = { contractAddress: addr, caseCommitment: commitment, revision: 1n, codeMatches: true };
    return { ledger, confirmation: { txId: "attest-tx", txHash: "bb".repeat(32), blockHeight: 11, blockTimestamp: 0 } };
  }),
  makeReceipt: (network: string, contract: string, caseId: unknown, ledger: ConfirmedLedger, conf: object) => ({
    format: "chaintrace-attestation-receipt-v1",
    network,
    contract_address: contract,
    case_id: caseId,
    revision: ledger.revision.toString(),
    commitment: ledger.caseCommitment,
    ...conf,
  }),
}));

// Fast KDF for tests.
vi.mock("../src/secret-vault.js", async (orig) => {
  const real = await orig<typeof import("../src/secret-vault.js")>();
  return { ...real, sealSecret: (s: Uint8Array, p: string, n: string) => real.sealSecret(s, p, n, 1_000) };
});

const { VerifyView } = await import("../dapp/src/VerifyView.js");
const { AttestView } = await import("../dapp/src/AttestView.js");

const sampleCase = { id: 5, name: "Bridge laundering", status: "OPEN", findings: [{ id: 1, title: "Hop", severity: "HIGH" }] };

function drop(index: number, text: string) {
  const inputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
  const file = new File([text], "bundle.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => text });
  fireEvent.change(inputs[index], { target: { files: [file] } });
}

beforeEach(() => {
  ledgerState.current = null;
  localStorage.clear();
});
afterEach(cleanup);

describe("reviewer view", () => {
  it("shows a match only when the bundle equals the confirmed commitment", async () => {
    const bundle = await createBundle(sampleCase);
    ledgerState.current = { contractAddress: ADDRESS, caseCommitment: bundle.commitment, revision: 1n, codeMatches: true };
    render(<VerifyView />);
    drop(0, JSON.stringify(bundle));
    await screen.findByText(bundle.commitment);
    fireEvent.change(screen.getByPlaceholderText("64 hex characters"), { target: { value: ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /Verify against Midnight/ }));
    expect(await screen.findByText(/Match: this is the attested version/)).toBeTruthy();
  });

  it("shows no match for a tampered case", async () => {
    const bundle = await createBundle(sampleCase);
    ledgerState.current = { contractAddress: ADDRESS, caseCommitment: bundle.commitment, revision: 1n, codeMatches: true };
    const forged = await createBundle({ ...sampleCase, name: "Edited" }, bundle.salt);
    render(<VerifyView />);
    drop(0, JSON.stringify(forged));
    await screen.findByText(forged.commitment);
    fireEvent.change(screen.getByPlaceholderText("64 hex characters"), { target: { value: ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /Verify against Midnight/ }));
    expect(await screen.findByText(/No match/)).toBeTruthy();
    expect(screen.getByText(/commitment-mismatch/)).toBeTruthy();
  });

  it("rejects a bundle whose salt was changed before any network call", async () => {
    const bundle = await createBundle(sampleCase);
    render(<VerifyView />);
    drop(0, JSON.stringify({ ...bundle, salt: "00".repeat(32) }));
    expect(await screen.findByText(/does not match the bundle's commitment/)).toBeTruthy();
  });
});

describe("investigator view", () => {
  it("deploys, attests, and shows Confirmed only after confirmation", async () => {
    const bundle = await createBundle(sampleCase);
    const wallet = { api: {}, name: "test", indexerUri: "", indexerWsUri: "", networkId: "preview" } as never;
    render(<AttestView wallet={wallet} onConnect={() => {}} />);
    drop(0, JSON.stringify(bundle));
    await screen.findByText(bundle.commitment);

    const [p1, p2] = document.querySelectorAll<HTMLInputElement>('input[type="password"]');
    fireEvent.change(p1, { target: { value: "a long passphrase" } });
    fireEvent.change(p2, { target: { value: "a long passphrase" } });
    fireEvent.click(screen.getByRole("button", { name: /Deploy contract and attest/ }));

    // Attestation is submitted but not yet confirmed.
    await waitFor(() => expect(gate.release).toBeTypeOf("function"));
    expect(screen.queryByText(/Confirmed on Midnight/)).toBeNull();
    expect(screen.getByText("attest-tx")).toBeTruthy();

    await act(async () => gate.release!());
    expect(await screen.findByText(/Confirmed on Midnight/)).toBeTruthy();
    expect(screen.getAllByText(bundle.commitment).length).toBeGreaterThan(0);

    // The owner secret is stored sealed, never in plaintext, and keyed to the new contract.
    const stored = localStorage.getItem(`chaintrace:owner-secret:preview:${ADDRESS}`);
    expect(stored).toContain("chaintrace-owner-secret-v1");
    expect(JSON.parse(stored!).ciphertext).toMatch(/^[0-9a-f]+$/);
  });

  it("keeps the attest button disabled until passphrases match", async () => {
    const bundle = await createBundle(sampleCase);
    const wallet = { api: {}, name: "test", indexerUri: "", indexerWsUri: "", networkId: "preview" } as never;
    render(<AttestView wallet={wallet} onConnect={() => {}} />);
    drop(0, JSON.stringify(bundle));
    await screen.findByText(bundle.commitment);
    const [p1, p2] = document.querySelectorAll<HTMLInputElement>('input[type="password"]');
    fireEvent.change(p1, { target: { value: "a long passphrase" } });
    fireEvent.change(p2, { target: { value: "a different one!" } });
    expect((screen.getByRole("button", { name: /Deploy contract and attest/ }) as HTMLButtonElement).disabled).toBe(true);
  });
});
