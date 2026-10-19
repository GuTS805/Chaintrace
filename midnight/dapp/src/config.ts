// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

// import.meta.env exists under Vite; scripts run with tsx see an empty object.
const env: Record<string, string | undefined> = import.meta.env ?? {};

export const config = {
  networkId: env.VITE_NETWORK_ID ?? "preview",
  indexerUri: env.VITE_INDEXER_URI ?? "https://indexer.preview.midnight.network/api/v4/graphql",
  indexerWsUri: env.VITE_INDEXER_WS_URI ?? "wss://indexer.preview.midnight.network/api/v4/graphql/ws",
  proofServerUri: env.VITE_PROOF_SERVER_URI ?? "http://localhost:6300",
  zkBaseUrl: typeof window === "undefined" ? "" : window.location.origin,
};
