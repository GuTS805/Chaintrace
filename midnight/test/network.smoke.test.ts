// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Opt-in live check against the Midnight Preview indexer:
//   MIDNIGHT_SMOKE=1 npx vitest run test/network.smoke.test.ts
// Set MIDNIGHT_CONTRACT to also read a deployed case contract.

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { indexerPublicDataProvider } from "@midnight-ntwrk/midnight-js-indexer-public-data-provider";
import { setNetworkId } from "@midnight-ntwrk/midnight-js-network-id";
import { CIRCUITS, type VerifierKeys, readConfirmedLedger } from "../src/ledger-read.js";

const INDEXER = process.env.MIDNIGHT_INDEXER ?? "https://indexer.preview.midnight.network/api/v4/graphql";
const INDEXER_WS = process.env.MIDNIGHT_INDEXER_WS ?? "wss://indexer.preview.midnight.network/api/v4/graphql/ws";
const keys = Object.fromEntries(
  CIRCUITS.map((c) => [c, new Uint8Array(readFileSync(new URL(`../managed/private_case/keys/${c}.verifier`, import.meta.url)))]),
) as VerifierKeys;

describe.runIf(process.env.MIDNIGHT_SMOKE === "1")("Midnight Preview indexer", () => {
  setNetworkId((process.env.MIDNIGHT_NETWORK ?? "preview") as never);
  const provider = indexerPublicDataProvider(INDEXER, INDEXER_WS, globalThis.WebSocket as never);

  it("returns no state for an address with no contract", async () => {
    expect(await readConfirmedLedger(provider, "00".repeat(32), keys)).toBeNull();
  }, 30_000);

  it.runIf(!!process.env.MIDNIGHT_CONTRACT)("reads a deployed case contract", async () => {
    const ledger = await readConfirmedLedger(provider, process.env.MIDNIGHT_CONTRACT!, keys);
    console.log(ledger);
    expect(ledger?.codeMatches).toBe(true);
  }, 30_000);
});
