// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Opt-in end-to-end test on a local standalone Midnight network (node, indexer
// and proof server in Docker). Exercises the DApp's real Midnight code path:
// wallet connector -> proof server -> wallet balancing -> submission ->
// finalization -> indexer ledger read -> reviewer verdict.
//
//   npm run test:e2e        (Docker must be running; first run pulls images)

import { appendFileSync, mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import {
  DAppConnectorWalletAdapter,
  LocalTestEnvironment,
  type MidnightWalletProvider,
  createDefaultTestLogger,
  defaultContainersConfiguration,
  setContainersConfiguration,
} from "@midnight-ntwrk/testkit-js";
import { NodeZkConfigProvider } from "@midnight-ntwrk/midnight-js-node-zk-config-provider";
import { setNetworkId } from "@midnight-ntwrk/midnight-js-network-id";
import { checkBundle, createBundle } from "../../src/bundle.js";
import { CIRCUITS, type VerifierKeys } from "../../src/ledger-read.js";
import { generateOwnerSecret } from "../../src/secret-vault.js";
import type { TxStage } from "../../src/tx-stages.js";
import { verdict } from "../../src/verify.js";
import {
  attestCase,
  buildProviders,
  deployCase,
  primeWalletKeys,
  readCase,
  rotateOwner,
  setZkSource,
} from "../../dapp/src/case-api.js";
import type { WalletConnection } from "../../dapp/src/wallet.js";
import type { PrivateCaseCircuit, PrivateCaseProviders } from "../../src/contract.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const managed = path.resolve(here, "../../managed/private_case");
const keys = Object.fromEntries(
  CIRCUITS.map((c) => [c, new Uint8Array(readFileSync(path.join(managed, "keys", `${c}.verifier`)))]),
) as VerifierKeys;

const MINUTE = 60_000;

/** Appends on-chain identifiers from this run to logs/e2e-evidence.jsonl. */
function record(event: string, data: Record<string, unknown>) {
  const dir = path.resolve(here, "../../logs");
  mkdirSync(dir, { recursive: true });
  appendFileSync(path.join(dir, "e2e-evidence.jsonl"), `${JSON.stringify({ at: new Date().toISOString(), event, ...data })}
`);
}
const caseV1 = {
  id: 9001,
  title: "E2E: mixer outflow",
  status: "OPEN",
  findings: [{ id: 1, severity: "HIGH", note: "Peel chain to exchange deposit" }],
};
const caseV2 = { ...caseV1, findings: [...caseV1.findings, { id: 2, severity: "MEDIUM", note: "Bridge hop" }] };

describe.runIf(process.env.MIDNIGHT_E2E === "1")("Chaintrace private case on a local Midnight network", () => {
  let env: LocalTestEnvironment;
  let walletProvider: MidnightWalletProvider;
  let providers: PrivateCaseProviders;
  let contractAddress = "";
  const owner = generateOwnerSecret();

  beforeAll(async () => {
    setContainersConfiguration({
      ...defaultContainersConfiguration,
      standalone: { ...defaultContainersConfiguration.standalone, path: here, fileName: "compose.yml" },
    });
    setNetworkId("undeployed");
    env = new LocalTestEnvironment(createDefaultTestLogger());
    const cfg = await env.start();
    walletProvider = await env.getMidnightWalletProvider();

    setZkSource({
      provider: () => new NodeZkConfigProvider<PrivateCaseCircuit>(managed),
      verifierKeys: async () => keys,
    });
    const wallet: WalletConnection = {
      api: new DAppConnectorWalletAdapter(walletProvider, cfg) as never,
      name: "testkit connector",
      indexerUri: cfg.indexer,
      indexerWsUri: cfg.indexerWS,
      proverServerUri: cfg.proofServer,
      networkId: cfg.networkId,
    };
    await primeWalletKeys(wallet);
    providers = buildProviders(wallet);
  }, 30 * MINUTE);

  afterAll(async () => {
    await env?.shutdown();
  }, 5 * MINUTE);

  it("deploys a case contract and reports honest stages", async () => {
    const stages: TxStage[] = [];
    const deployed = await deployCase(providers, owner, (s) => stages.push(s));
    contractAddress = deployed.contractAddress;
    expect(contractAddress).toMatch(/^[0-9a-f]{64}$/);
    expect(deployed.ledger).toMatchObject({ revision: 0n, codeMatches: true });
    record("deploy", { contract: contractAddress, tx: deployed.confirmation.txHash, block: deployed.confirmation.blockHeight });
    const names = stages.map((s) => s.stage);
    expect(names.indexOf("submitted")).toBeGreaterThan(names.indexOf("prepared"));
    expect(names.at(-1)).toBe("confirmed");
  }, 15 * MINUTE);

  it("attests revision 1 and a reviewer verifies the bundle", async () => {
    const bundle = await createBundle(caseV1);
    const stages: TxStage[] = [];
    const result = await attestCase(providers, contractAddress, owner, bundle.commitment, (s) => stages.push(s));
    expect(result.ledger.revision).toBe(1n);
    expect(result.confirmation.blockHeight).toBeGreaterThan(0);
    record("attest", {
      revision: 1,
      commitment: bundle.commitment,
      tx: result.confirmation.txHash,
      block: result.confirmation.blockHeight,
    });
    expect(stages.map((s) => s.stage)).toEqual(["proving", "balancing", "prepared", "submitted", "confirmed"]);

    const onChain = await readCase(providers.publicDataProvider, contractAddress);
    expect(verdict(await checkBundle(bundle), onChain, 1n)).toMatchObject({ status: "verified", revision: 1n });

    const tampered = { ...bundle, case: { ...bundle.case, title: "Edited after attestation" } };
    expect(verdict(await checkBundle(tampered), onChain).status).toBe("failed");
    expect(verdict(await checkBundle({ ...bundle, salt: "00".repeat(32) }), onChain).status).toBe("failed");
  }, 15 * MINUTE);

  it("rejects an attestation without the owner secret and leaves the ledger unchanged", async () => {
    const forged = await createBundle({ ...caseV1, title: "Forged" });
    await expect(
      attestCase(providers, contractAddress, generateOwnerSecret(), forged.commitment, () => {}),
    ).rejects.toThrow(/Unauthorized/);
    expect((await readCase(providers.publicDataProvider, contractAddress))?.revision).toBe(1n);
  }, 15 * MINUTE);

  it("attests revision 2; the revision 1 bundle is then reported as superseded", async () => {
    const v1 = await createBundle(caseV1);
    const v2 = await createBundle(caseV2);
    const r2 = await attestCase(providers, contractAddress, owner, v2.commitment, () => {});
    record("attest", { revision: 2, commitment: v2.commitment, tx: r2.confirmation.txHash, block: r2.confirmation.blockHeight });
    const onChain = await readCase(providers.publicDataProvider, contractAddress);
    expect(onChain?.revision).toBe(2n);
    expect(verdict(await checkBundle(v2), onChain, 2n).status).toBe("verified");
    expect(verdict(await checkBundle(v1), onChain, 1n)).toMatchObject({ reason: "superseded" });
  }, 15 * MINUTE);

  it("rotates the owner: the old secret stops working, the new one works", async () => {
    const next = generateOwnerSecret();
    const rot = await rotateOwner(providers, contractAddress, owner, next, () => {});
    record("rotate_owner", { tx: rot.txHash, block: rot.blockHeight });
    const v3 = await createBundle({ ...caseV2, status: "CLOSED" });
    await expect(attestCase(providers, contractAddress, owner, v3.commitment, () => {})).rejects.toThrow(
      /Unauthorized/,
    );
    const result = await attestCase(providers, contractAddress, next, v3.commitment, () => {});
    expect(result.ledger.revision).toBe(3n);
  }, 20 * MINUTE);

  it("reports a missing contract for an unknown address", async () => {
    const bundle = await createBundle(caseV1);
    expect(verdict(await checkBundle(bundle), await readCase(providers.publicDataProvider, "ab".repeat(32)))).toMatchObject({
      reason: "contract-not-found",
    });
  }, 5 * MINUTE);
});
