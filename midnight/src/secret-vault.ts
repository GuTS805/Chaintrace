// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
//
// Owner secret at rest: AES-256-GCM under a key derived from the investigator's
// passphrase (PBKDF2-SHA256). Stored separately from case data, keyed by network
// and contract address. The plaintext secret exists only in memory while a
// transaction is being prepared.
//
// Limitation: there is no recovery. Losing both the passphrase and every sealed
// copy means the case can never be attested again; a new deployment is required.

import { fromHex, randomBytes, toHex } from "./hex.js";

export const SEALED_FORMAT = "chaintrace-owner-secret-v1";
export const PBKDF2_ITERATIONS = 600_000;
export const MIN_PASSPHRASE_LENGTH = 12;

export interface SealedSecret {
  format: typeof SEALED_FORMAT;
  network: string;
  contract_address: string | null;
  kdf: "PBKDF2-SHA256";
  iterations: number;
  salt: string;
  iv: string;
  ciphertext: string;
  created_at: string;
}

async function deriveKey(passphrase: string, salt: Uint8Array, iterations: number): Promise<CryptoKey> {
  const material = await crypto.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, [
    "deriveKey",
  ]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt: salt as BufferSource, iterations },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

function aad(network: string): Uint8Array {
  return new TextEncoder().encode(`${SEALED_FORMAT}:${network}`);
}

export function generateOwnerSecret(): Uint8Array {
  return randomBytes(32);
}

export async function sealSecret(
  secret: Uint8Array,
  passphrase: string,
  network: string,
  iterations: number = PBKDF2_ITERATIONS,
): Promise<SealedSecret> {
  if (secret.length !== 32) throw new Error("Owner secret must be 32 bytes");
  if (passphrase.length < MIN_PASSPHRASE_LENGTH) {
    throw new Error(`Passphrase must be at least ${MIN_PASSPHRASE_LENGTH} characters`);
  }
  const salt = randomBytes(16);
  const iv = randomBytes(12);
  const key = await deriveKey(passphrase, salt, iterations);
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv as BufferSource, additionalData: aad(network) as BufferSource },
    key,
    secret as BufferSource,
  );
  return {
    format: SEALED_FORMAT,
    network,
    contract_address: null,
    kdf: "PBKDF2-SHA256",
    iterations,
    salt: toHex(salt),
    iv: toHex(iv),
    ciphertext: toHex(new Uint8Array(ciphertext)),
    created_at: new Date().toISOString(),
  };
}

export async function openSecret(sealed: SealedSecret, passphrase: string): Promise<Uint8Array> {
  if (sealed.format !== SEALED_FORMAT) throw new Error("Unsupported owner secret file");
  const key = await deriveKey(passphrase, fromHex(sealed.salt), sealed.iterations);
  try {
    const plain = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: fromHex(sealed.iv) as BufferSource, additionalData: aad(sealed.network) as BufferSource },
      key,
      fromHex(sealed.ciphertext) as BufferSource,
    );
    return new Uint8Array(plain);
  } catch {
    throw new Error("Wrong passphrase or damaged owner secret file");
  }
}

export function isSealedSecret(value: unknown): value is SealedSecret {
  const v = value as Partial<SealedSecret> | null;
  return (
    !!v &&
    v.format === SEALED_FORMAT &&
    typeof v.network === "string" &&
    typeof v.salt === "string" &&
    typeof v.iv === "string" &&
    typeof v.ciphertext === "string" &&
    typeof v.iterations === "number"
  );
}

/** Minimal storage interface so the vault works with localStorage or an in-memory map in tests. */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

const PREFIX = "chaintrace:owner-secret";

export class SecretVault {
  constructor(private readonly store: KeyValueStore) {}

  private key(network: string, contractAddress: string): string {
    return `${PREFIX}:${network}:${contractAddress}`;
  }

  private pendingKey(network: string, contractAddress: string | null): string {
    return `${PREFIX}:pending:${network}:${contractAddress ?? "new-deployment"}`;
  }

  get(network: string, contractAddress: string): SealedSecret | null {
    const raw = this.store.getItem(this.key(network, contractAddress));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return isSealedSecret(parsed) ? parsed : null;
  }

  put(sealed: SealedSecret, contractAddress: string): SealedSecret {
    const bound = { ...sealed, contract_address: contractAddress };
    this.store.setItem(this.key(sealed.network, contractAddress), JSON.stringify(bound));
    return bound;
  }

  /**
   * Keeps a sealed secret for an in-flight deployment or rotation, so it is not
   * lost if the page closes between submission and confirmation.
   */
  putPending(sealed: SealedSecret, contractAddress: string | null): void {
    this.store.setItem(this.pendingKey(sealed.network, contractAddress), JSON.stringify(sealed));
  }

  getPending(network: string, contractAddress: string | null): SealedSecret | null {
    const raw = this.store.getItem(this.pendingKey(network, contractAddress));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return isSealedSecret(parsed) ? parsed : null;
  }

  clearPending(network: string, contractAddress: string | null): void {
    this.store.removeItem(this.pendingKey(network, contractAddress));
  }
}

export function memoryStore(): KeyValueStore & { dump(): Map<string, string> } {
  const map = new Map<string, string>();
  return {
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => void map.set(k, v),
    removeItem: (k) => void map.delete(k),
    dump: () => map,
  };
}
