// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

export const config = {
  networkId: (import.meta.env.VITE_NETWORK_ID as string | undefined) ?? "preview",
  indexerUri:
    (import.meta.env.VITE_INDEXER_URI as string | undefined) ?? "https://indexer.preview.midnight.network/api/v4/graphql",
  indexerWsUri:
    (import.meta.env.VITE_INDEXER_WS_URI as string | undefined) ??
    "wss://indexer.preview.midnight.network/api/v4/graphql/ws",
  proofServerUri: (import.meta.env.VITE_PROOF_SERVER_URI as string | undefined) ?? "http://localhost:6300",
  zkBaseUrl: typeof window === "undefined" ? "" : window.location.origin,
};
