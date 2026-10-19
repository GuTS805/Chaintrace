// Copyright 2026 Chaintrace contributors.
// Portions adapted from midnightntwrk/example-bboard, Copyright (C) Midnight Foundation.
// SPDX-License-Identifier: Apache-2.0

import "@midnight-ntwrk/dapp-connector-api";
import type { ConnectedAPI, InitialAPI } from "@midnight-ntwrk/dapp-connector-api";
import semver from "semver";

const COMPATIBLE_CONNECTOR_API = "4.x";

function findWallet(): InitialAPI | undefined {
  const injected = (window as unknown as { midnight?: Record<string, unknown> }).midnight;
  if (!injected) return undefined;
  return Object.values(injected).find(
    (w): w is InitialAPI =>
      !!w &&
      typeof w === "object" &&
      "apiVersion" in w &&
      semver.satisfies(String((w as InitialAPI).apiVersion), COMPATIBLE_CONNECTOR_API),
  );
}

async function waitForWallet(timeoutMs: number): Promise<InitialAPI> {
  const started = Date.now();
  for (;;) {
    const wallet = findWallet();
    if (wallet) return wallet;
    if (Date.now() - started > timeoutMs) {
      throw new Error("No Midnight wallet found. Install Lace with Midnight support and enable it for this site.");
    }
    await new Promise((r) => setTimeout(r, 100));
  }
}

export interface WalletConnection {
  api: ConnectedAPI;
  name: string;
  indexerUri: string;
  indexerWsUri: string;
  proverServerUri?: string;
  networkId: string;
}

export async function connectWallet(networkId: string): Promise<WalletConnection> {
  const initial = await waitForWallet(2_000);
  const api = await initial.connect(networkId);
  const cfg = await api.getConfiguration();
  if (cfg.networkId !== networkId) {
    throw new Error(`Wallet is on network "${cfg.networkId}", but this DApp is configured for "${networkId}".`);
  }
  return {
    api,
    name: String((initial as unknown as { name?: string }).name ?? "Midnight wallet"),
    indexerUri: cfg.indexerUri,
    indexerWsUri: cfg.indexerWsUri,
    proverServerUri: cfg.proverServerUri,
    networkId: cfg.networkId,
  };
}
