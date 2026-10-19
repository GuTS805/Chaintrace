// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Midnight operations for one case contract. Every write follows the same rule:
// report "confirmed" only after the finalized transaction succeeded AND a fresh
// read of the ledger shows the expected state.

import { deployContract, findDeployedContract } from "@midnight-ntwrk/midnight-js-contracts";
import { FetchZkConfigProvider } from "@midnight-ntwrk/midnight-js-fetch-zk-config-provider";
import { httpClientProofProvider } from "@midnight-ntwrk/midnight-js-http-client-proof-provider";
import { indexerPublicDataProvider } from "@midnight-ntwrk/midnight-js-indexer-public-data-provider";
import { fromHex as protocolFromHex, toHex as protocolToHex } from "@midnight-ntwrk/midnight-js-protocol/compact-runtime";
import {
  type Binding,
  type FinalizedTransaction,
  type Proof,
  type SignatureEnabled,
  Transaction,
} from "@midnight-ntwrk/midnight-js-protocol/ledger";
import {
  SucceedEntirely,
  type FinalizedTxData,
  type PublicDataProvider,
  type ZKConfigProvider,
} from "@midnight-ntwrk/midnight-js-types";
import type { UnboundTransaction } from "@midnight-ntwrk/midnight-js-types";
import { CompiledPrivateCase, PrivateCase, type PrivateCaseCircuit, type PrivateCaseProviders } from "../../src/contract.js";
import { fromHex, toHex } from "../../src/hex.js";
import { type VerifierKeys, fetchVerifierKeys, readConfirmedLedger } from "../../src/ledger-read.js";
import { type TxStage, instrumentProviders } from "../../src/tx-stages.js";
import type { ConfirmedLedger } from "../../src/verify.js";
import { type CasePrivateState, casePrivateStateId } from "../../src/witnesses.js";
import { config } from "./config.js";
import { inMemoryPrivateStateProvider } from "./private-state.js";
import type { WalletConnection } from "./wallet.js";

export type StageListener = (stage: TxStage) => void;

export interface Confirmation {
  txId: string;
  txHash: string;
  blockHeight: number;
  blockTimestamp: number;
}

export interface AttestationReceipt extends Confirmation {
  format: "chaintrace-attestation-receipt-v1";
  network: string;
  contract_address: string;
  case_id: string | number | null;
  revision: string;
  commitment: string;
}

/** Where proving/verifier keys come from. The browser fetches them from this origin; tests read them from disk. */
export interface ZkSource {
  provider(): ZKConfigProvider<PrivateCaseCircuit>;
  verifierKeys(): Promise<VerifierKeys>;
}

let browserKeys: Promise<VerifierKeys> | undefined;
let zk: ZkSource = {
  provider: () => new FetchZkConfigProvider<PrivateCaseCircuit>(config.zkBaseUrl, fetch.bind(globalThis)),
  verifierKeys: () => (browserKeys ??= fetchVerifierKeys(config.zkBaseUrl)),
};

export function setZkSource(source: ZkSource): void {
  zk = source;
}

export function verifierKeys(): Promise<VerifierKeys> {
  return zk.verifierKeys();
}

export function readOnlyPublicData(): PublicDataProvider {
  return indexerPublicDataProvider(config.indexerUri, config.indexerWsUri, globalThis.WebSocket as never);
}

export async function readCase(publicData: PublicDataProvider, contractAddress: string): Promise<ConfirmedLedger | null> {
  return readConfirmedLedger(publicData, contractAddress.trim().toLowerCase(), await verifierKeys());
}

export function buildProviders(wallet: WalletConnection): PrivateCaseProviders {
  const zkConfigProvider = zk.provider();
  return {
    privateStateProvider: inMemoryPrivateStateProvider<typeof casePrivateStateId, CasePrivateState>(),
    zkConfigProvider,
    proofProvider: httpClientProofProvider(wallet.proverServerUri ?? config.proofServerUri, zkConfigProvider),
    publicDataProvider: indexerPublicDataProvider(wallet.indexerUri, wallet.indexerWsUri, globalThis.WebSocket as never),
    walletProvider: {
      getCoinPublicKey: () => walletKeys(wallet).shieldedCoinPublicKey,
      getEncryptionPublicKey: () => walletKeys(wallet).shieldedEncryptionPublicKey,
      balanceTx: async (tx: UnboundTransaction): Promise<FinalizedTransaction> => {
        const received = await wallet.api.balanceUnsealedTransaction(protocolToHex(tx.serialize()));
        return Transaction.deserialize<SignatureEnabled, Proof, Binding>(
          "signature",
          "proof",
          "binding",
          protocolFromHex(received.tx),
        );
      },
    },
    midnightProvider: {
      submitTx: async (tx: FinalizedTransaction) => {
        await wallet.api.submitTransaction(protocolToHex(tx.serialize()));
        return tx.identifiers()[0];
      },
    },
  };
}

// The connector returns addresses asynchronously; cache them once at connect time.
const keyCache = new WeakMap<WalletConnection, { shieldedCoinPublicKey: string; shieldedEncryptionPublicKey: string }>();
export async function primeWalletKeys(wallet: WalletConnection): Promise<void> {
  const addresses = await wallet.api.getShieldedAddresses();
  keyCache.set(wallet, addresses);
}
function walletKeys(wallet: WalletConnection) {
  const keys = keyCache.get(wallet);
  if (!keys) throw new Error("Wallet keys not loaded");
  return keys;
}

function confirmation(data: FinalizedTxData): Confirmation {
  if (data.status !== SucceedEntirely) throw new Error(`Transaction was not applied (status ${data.status})`);
  return {
    txId: String(data.txId),
    txHash: String(data.txHash),
    blockHeight: data.blockHeight,
    blockTimestamp: data.blockTimestamp,
  };
}

async function withSecret<T>(
  providers: PrivateCaseProviders,
  contractAddress: string | null,
  run: () => Promise<T>,
): Promise<T> {
  try {
    return await run();
  } finally {
    if (contractAddress) {
      providers.privateStateProvider.setContractAddress(contractAddress);
      await providers.privateStateProvider.remove(casePrivateStateId);
    }
  }
}

/** Deploys a new case contract owned by `ownerSecret`. */
export async function deployCase(
  base: PrivateCaseProviders,
  ownerSecret: Uint8Array,
  onStage: StageListener,
): Promise<{ contractAddress: string; ledger: ConfirmedLedger; confirmation: Confirmation }> {
  const providers = instrumentProviders(base, onStage);
  const deployed = await deployContract(providers, {
    compiledContract: CompiledPrivateCase,
    privateStateId: casePrivateStateId,
    initialPrivateState: { ownerSecret },
  });
  const address = deployed.deployTxData.public.contractAddress;
  return withSecret(base, address, async () => {
    const conf = confirmation(deployed.deployTxData.public);
    const ledger = await readCase(base.publicDataProvider, address);
    const expectedOwner = toHex(PrivateCase.pureCircuits.derive_owner_key(ownerSecret));
    if (!ledger?.codeMatches || (await ownerKeyHex(base, address)) !== expectedOwner) {
      throw new Error("Deployment finalized, but the confirmed ledger does not show this owner");
    }
    onStage({ stage: "confirmed", txId: conf.txId, txHash: conf.txHash, blockHeight: conf.blockHeight });
    return { contractAddress: address, ledger, confirmation: conf };
  });
}

async function ownerKeyHex(providers: PrivateCaseProviders, address: string): Promise<string> {
  const state = await providers.publicDataProvider.queryContractState(address);
  if (!state) throw new Error("Contract state not found");
  return toHex(PrivateCase.ledger(state.data).owner_key);
}

async function join(providers: PrivateCaseProviders, contractAddress: string, ownerSecret: Uint8Array) {
  return findDeployedContract(providers, {
    contractAddress,
    compiledContract: CompiledPrivateCase,
    privateStateId: casePrivateStateId,
    initialPrivateState: { ownerSecret },
  });
}

/** Records `commitmentHex` as the next revision of the case. */
export async function attestCase(
  base: PrivateCaseProviders,
  contractAddress: string,
  ownerSecret: Uint8Array,
  commitmentHex: string,
  onStage: StageListener,
): Promise<{ ledger: ConfirmedLedger; confirmation: Confirmation }> {
  const before = await readCase(base.publicDataProvider, contractAddress);
  if (!before) throw new Error("No confirmed case contract at this address");
  if (!before.codeMatches) throw new Error("The contract at this address is not a Chaintrace case contract");
  if (before.caseCommitment === commitmentHex) throw new Error(`This commitment is already revision ${before.revision}`);

  const providers = instrumentProviders(base, onStage);
  return withSecret(base, contractAddress, async () => {
    const contract = await join(providers, contractAddress, ownerSecret);
    const result = await contract.callTx.attest(before.revision, fromHex(commitmentHex));
    const conf = confirmation(result.public);
    const after = await readCase(base.publicDataProvider, contractAddress);
    if (!after || after.caseCommitment !== commitmentHex || after.revision !== before.revision + 1n) {
      throw new Error("Transaction finalized, but the confirmed ledger does not show this commitment");
    }
    onStage({ stage: "confirmed", txId: conf.txId, txHash: conf.txHash, blockHeight: conf.blockHeight });
    return { ledger: after, confirmation: conf };
  });
}

/** Moves ownership to `newSecret`. The caller must have sealed and saved `newSecret` first. */
export async function rotateOwner(
  base: PrivateCaseProviders,
  contractAddress: string,
  currentSecret: Uint8Array,
  newSecret: Uint8Array,
  onStage: StageListener,
): Promise<Confirmation> {
  const providers = instrumentProviders(base, onStage);
  const newKey = PrivateCase.pureCircuits.derive_owner_key(newSecret);
  return withSecret(base, contractAddress, async () => {
    const contract = await join(providers, contractAddress, currentSecret);
    const result = await contract.callTx.rotate_owner(newKey);
    const conf = confirmation(result.public);
    if ((await ownerKeyHex(base, contractAddress)) !== toHex(newKey)) {
      throw new Error("Rotation finalized, but the confirmed ledger does not show the new owner key");
    }
    onStage({ stage: "confirmed", txId: conf.txId, txHash: conf.txHash, blockHeight: conf.blockHeight });
    return conf;
  });
}

export function makeReceipt(
  network: string,
  contractAddress: string,
  caseId: string | number | null,
  ledger: ConfirmedLedger,
  conf: Confirmation,
): AttestationReceipt {
  return {
    format: "chaintrace-attestation-receipt-v1",
    network,
    contract_address: contractAddress,
    case_id: caseId,
    revision: ledger.revision.toString(),
    commitment: ledger.caseCommitment,
    ...conf,
  };
}

export function isReceipt(value: unknown): value is AttestationReceipt {
  const r = value as Partial<AttestationReceipt> | null;
  return !!r && r.format === "chaintrace-attestation-receipt-v1" && typeof r.contract_address === "string";
}
