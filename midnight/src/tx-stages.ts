// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Wraps Midnight.js providers so the UI can report honest transaction stages.
// "confirmed" is never emitted here: it is set only after the finalized
// transaction is observed and the ledger is re-read (see dapp/src/case-api.ts).

import type { MidnightProviders } from "@midnight-ntwrk/midnight-js-types";

export type TxStage =
  | { stage: "idle" }
  | { stage: "proving" }
  | { stage: "balancing" }
  | { stage: "prepared" }
  | { stage: "submitted"; txId: string }
  | { stage: "confirmed"; txId: string; txHash: string; blockHeight: number }
  | { stage: "failed"; error: string };

export function instrumentProviders<P extends MidnightProviders<any, any, any>>(
  providers: P,
  onStage: (stage: TxStage) => void,
): P {
  return {
    ...providers,
    proofProvider: {
      ...providers.proofProvider,
      proveTx: (tx, config) => {
        onStage({ stage: "proving" });
        return providers.proofProvider.proveTx(tx, config);
      },
    },
    walletProvider: {
      getCoinPublicKey: () => providers.walletProvider.getCoinPublicKey(),
      getEncryptionPublicKey: () => providers.walletProvider.getEncryptionPublicKey(),
      balanceTx: async (tx, ttl) => {
        onStage({ stage: "balancing" });
        const balanced = await providers.walletProvider.balanceTx(tx, ttl);
        onStage({ stage: "prepared" });
        return balanced;
      },
    },
    midnightProvider: {
      submitTx: async (tx) => {
        const txId = await providers.midnightProvider.submitTx(tx);
        onStage({ stage: "submitted", txId: String(txId) });
        return txId;
      },
    },
  };
}

export function describeStage(stage: TxStage): string {
  switch (stage.stage) {
    case "idle":
      return "Not started";
    case "proving":
      return "Generating zero-knowledge proof locally";
    case "balancing":
      return "Waiting for the wallet to balance and sign";
    case "prepared":
      return "Prepared: proven and signed, not yet submitted";
    case "submitted":
      return "Submitted: waiting for the transaction to be included in a block";
    case "confirmed":
      return `Confirmed in block ${stage.blockHeight}`;
    case "failed":
      return `Failed: ${stage.error}`;
  }
}
