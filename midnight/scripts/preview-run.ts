// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Attests a demo case on the public Midnight Preview network with a headless
// wallet, then verifies it the way a reviewer would. Uses the DApp's own code
// (dapp/src/case-api.ts) through testkit's DApp-connector adapter.
//
//   npm run preview:run
//
// First run: creates a test wallet in .preview/ (gitignored) and prints its
// address. Fund it once at https://faucet.preview.midnight.network (captcha),
// and the script continues by itself. Re-running reuses the wallet and contract
// and attests a new revision.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pino } from "pino";
import * as Rx from "rxjs";
import {
  DAppConnectorWalletAdapter,
  MidnightWalletProvider,
  PreviewTestEnvironment,
  waitForFunds,
} from "@midnight-ntwrk/testkit-js";
import { setNetworkId } from "@midnight-ntwrk/midnight-js-network-id";
import { NodeZkConfigProvider } from "@midnight-ntwrk/midnight-js-node-zk-config-provider";
import { unshieldedToken } from "@midnight-ntwrk/midnight-js-protocol/ledger";
import { checkBundle, createBundle, type CaseSnapshot } from "../src/bundle.js";
import { CIRCUITS, type VerifierKeys } from "../src/ledger-read.js";
import { generateOwnerSecret, openSecret, sealSecret, type SealedSecret } from "../src/secret-vault.js";
import { randomBytes, toHex } from "../src/hex.js";
import { verdict } from "../src/verify.js";
import type { TxStage } from "../src/tx-stages.js";
import { describeStage } from "../src/tx-stages.js";
import type { PrivateCaseCircuit } from "../src/contract.js";
import {
  attestCase,
  buildProviders,
  deployCase,
  makeReceipt,
  primeWalletKeys,
  readCase,
  readOnlyPublicData,
  setZkSource,
} from "../dapp/src/case-api.js";
import type { WalletConnection } from "../dapp/src/wallet.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const stateDir = path.join(root, ".preview");
const managed = path.join(root, "managed/private_case");
const FAUCET_PAGE = "https://faucet.preview.midnight.network";
const PROOF_SERVER = process.env.PROOF_SERVER_URL ?? "http://localhost:6300";

interface PreviewState {
  seed: string;
  passphrase: string;
  contractAddress?: string;
  sealedOwner?: SealedSecret;
  revisions: Array<{ revision: string; commitment: string; tx: string; block: number; at: string }>;
}

const log = (msg: string) => console.log(`[preview] ${msg}`);
const statePath = path.join(stateDir, "state.json");

function loadState(): PreviewState {
  mkdirSync(stateDir, { recursive: true });
  if (existsSync(statePath)) return JSON.parse(readFileSync(statePath, "utf8")) as PreviewState;
  const state: PreviewState = { seed: toHex(randomBytes(32)), passphrase: toHex(randomBytes(16)), revisions: [] };
  saveState(state);
  return state;
}

function saveState(state: PreviewState) {
  writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
}

async function ensureProofServer() {
  try {
    const res = await fetch(`${PROOF_SERVER}/version`);
    if (res.ok) return log(`proof server ${PROOF_SERVER} is up (${(await res.text()).trim()})`);
  } catch {
    /* not running */
  }
  throw new Error(`No proof server at ${PROOF_SERVER}. Start it with: npm run proof-server`);
}

function demoCase(revision: number): CaseSnapshot {
  const findings = [
    { id: 1, title: "Peel chain into exchange deposit", severity: "HIGH", wallet_address: "0x9f2c…a41d" },
    { id: 2, title: "Bridge hop to Tron", severity: "MEDIUM", wallet_address: "TQ7x…8kPz" },
  ];
  if (revision > 1) findings.push({ id: 3, title: "Cash-out cluster linked", severity: "CRITICAL", wallet_address: "0x4b1e…07cc" });
  return {
    id: 4242,
    name: "Preview demo: mixer outflow review",
    status: revision > 1 ? "IN_REVIEW" : "OPEN",
    investigator: "demo-officer",
    findings,
  };
}

async function main() {
  const state = loadState();
  setNetworkId("preview");
  const quiet = pino({ level: "warn" }); // the wallet builder logs the seed at info level

  await ensureProofServer();
  const env = { ...new PreviewTestEnvironment(quiet).getEnvironmentConfiguration(), proofServer: PROOF_SERVER };

  log("building wallet (state kept in .preview/state.json)…");
  const walletProvider = await MidnightWalletProvider.build(quiet, env, state.seed);
  await walletProvider.start(false);
  const address = walletProvider.unshieldedKeystore.getBech32Address().asString();

  try {
    const night = unshieldedToken().raw;
    const funded = (s: { unshielded: { balances: Record<string, bigint> } }) => (s.unshielded.balances[night] ?? 0n) > 0n;
    if (!funded(await Rx.firstValueFrom(walletProvider.wallet.state()))) {
      log("──────────────────────────────────────────────────────────────");
      log(`Fund this wallet with tNIGHT at ${FAUCET_PAGE}`);
      log(`Address: ${address}`);
      log("Waiting for funds (leave this running)…");
      log("──────────────────────────────────────────────────────────────");
      writeFileSync(path.join(stateDir, "ADDRESS.txt"), `${address}\n`);
    }
    await Rx.firstValueFrom(walletProvider.wallet.state().pipe(Rx.filter(funded)));
    log("tNIGHT received; syncing and registering for DUST if needed…");
    const balance = await waitForFunds(walletProvider.wallet, env, false, walletProvider.unshieldedKeystore);
    log(`NIGHT balance: ${balance}`);
    const dust = await Rx.firstValueFrom(
      walletProvider.wallet.state().pipe(
        Rx.map((s) => s.dust.balance(new Date())),
        Rx.filter((d) => d > 0n),
        Rx.timeout(15 * 60_000),
      ),
    );
    log(`DUST balance: ${dust}`);

    setZkSource({
      provider: () => new NodeZkConfigProvider<PrivateCaseCircuit>(managed),
      verifierKeys: async () =>
        Object.fromEntries(
          CIRCUITS.map((c) => [c, new Uint8Array(readFileSync(path.join(managed, "keys", `${c}.verifier`)))]),
        ) as VerifierKeys,
    });
    const wallet: WalletConnection = {
      api: new DAppConnectorWalletAdapter(walletProvider, env) as never,
      name: "headless wallet-sdk",
      indexerUri: env.indexer,
      indexerWsUri: env.indexerWS,
      proverServerUri: env.proofServer,
      networkId: "preview",
    };
    await primeWalletKeys(wallet);
    const providers = buildProviders(wallet);
    const onStage = (s: TxStage) => log(`  ${describeStage(s)}`);

    let ownerSecret: Uint8Array;
    if (!state.contractAddress) {
      ownerSecret = generateOwnerSecret();
      state.sealedOwner = await sealSecret(ownerSecret, state.passphrase, "preview");
      saveState(state); // persist before submitting
      log("deploying case contract…");
      const deployed = await deployCase(providers, ownerSecret, onStage);
      state.contractAddress = deployed.contractAddress;
      state.sealedOwner = { ...state.sealedOwner, contract_address: deployed.contractAddress };
      saveState(state);
      log(`contract ${deployed.contractAddress} (tx ${deployed.confirmation.txHash}, block ${deployed.confirmation.blockHeight})`);
    } else {
      ownerSecret = await openSecret(state.sealedOwner!, state.passphrase);
      log(`reusing contract ${state.contractAddress}`);
    }

    const current = await readCase(providers.publicDataProvider, state.contractAddress!);
    const nextRevision = Number(current?.revision ?? 0n) + 1;
    const bundle = await createBundle(demoCase(nextRevision));
    writeFileSync(path.join(stateDir, `bundle-r${nextRevision}.json`), `${JSON.stringify(bundle, null, 2)}\n`);

    log(`attesting revision ${nextRevision}, commitment ${bundle.commitment}…`);
    const result = await attestCase(providers, state.contractAddress!, ownerSecret, bundle.commitment, onStage);
    ownerSecret.fill(0);
    const receipt = makeReceipt("preview", state.contractAddress!, bundle.case.id, result.ledger, result.confirmation);
    writeFileSync(path.join(stateDir, `receipt-r${nextRevision}.json`), `${JSON.stringify(receipt, null, 2)}\n`);
    state.revisions.push({
      revision: receipt.revision,
      commitment: receipt.commitment,
      tx: receipt.txHash,
      block: receipt.blockHeight,
      at: new Date().toISOString(),
    });
    saveState(state);

    // Reviewer check, as the DApp's Verify tab does it: public indexer, no wallet.
    const reviewerView = await readCase(readOnlyPublicData(), state.contractAddress!);
    const ok = verdict(await checkBundle(bundle), reviewerView, BigInt(receipt.revision));
    const tampered = verdict(
      await checkBundle({ ...bundle, case: { ...bundle.case, status: "CLOSED" } }),
      reviewerView,
    );
    log(`reviewer verdict: ${ok.status}${ok.status === "failed" ? ` (${ok.reason})` : ""}`);
    log(`tampered bundle: ${tampered.status === "failed" ? `rejected (${tampered.reason})` : "ACCEPTED (unexpected)"}`);
    log(`receipt: .preview/receipt-r${nextRevision}.json`);
    console.log(JSON.stringify({ contract: state.contractAddress, ...receipt, verdict: ok.status }, null, 2));
    if (ok.status !== "verified" || tampered.status !== "failed") process.exitCode = 1;
  } finally {
    await walletProvider.stop();
  }
}

main().catch((err) => {
  console.error(`[preview] failed: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
