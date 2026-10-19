// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { type TxStage, instrumentProviders } from "../src/tx-stages.js";

function fakeProviders(fail?: "prove" | "submit") {
  return {
    proofProvider: {
      proveTx: async () => {
        if (fail === "prove") throw new Error("prover down");
        return "proven";
      },
    },
    walletProvider: {
      getCoinPublicKey: () => "coin",
      getEncryptionPublicKey: () => "enc",
      balanceTx: async () => "balanced",
    },
    midnightProvider: {
      submitTx: async () => {
        if (fail === "submit") throw new Error("rejected");
        return "tx-1";
      },
    },
    publicDataProvider: {},
    privateStateProvider: {},
    zkConfigProvider: {},
  } as any;
}

async function drive(p: any) {
  await p.proofProvider.proveTx("unproven");
  await p.walletProvider.balanceTx("unbound");
  return p.midnightProvider.submitTx("final");
}

describe("transaction stage instrumentation", () => {
  it("reports proving, balancing, prepared and submitted in order, never confirmed", async () => {
    const stages: TxStage[] = [];
    const p = instrumentProviders(fakeProviders(), (s) => stages.push(s));
    expect(await drive(p)).toBe("tx-1");
    expect(stages.map((s) => s.stage)).toEqual(["proving", "balancing", "prepared", "submitted"]);
    expect(stages.at(-1)).toEqual({ stage: "submitted", txId: "tx-1" });
  });

  it("does not report submitted when submission fails", async () => {
    const stages: TxStage[] = [];
    const p = instrumentProviders(fakeProviders("submit"), (s) => stages.push(s));
    await expect(drive(p)).rejects.toThrow("rejected");
    expect(stages.map((s) => s.stage)).not.toContain("submitted");
  });

  it("passes wallet keys through", () => {
    const p = instrumentProviders(fakeProviders(), () => {});
    expect(p.walletProvider.getCoinPublicKey()).toBe("coin");
  });
});
