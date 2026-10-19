// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { SecretVault, generateOwnerSecret, memoryStore, openSecret, sealSecret } from "../src/secret-vault.js";
import { toHex } from "../src/hex.js";

// Low iteration count keeps the test fast; production uses PBKDF2_ITERATIONS.
const FAST = 1_000;
const PASS = "correct horse battery";

describe("owner secret vault", () => {
  it("round-trips a secret and never stores it in plaintext", async () => {
    const secret = generateOwnerSecret();
    const sealed = await sealSecret(secret, PASS, "preview", FAST);
    expect(await openSecret(sealed, PASS)).toEqual(secret);
    const store = memoryStore();
    new SecretVault(store).put(sealed, "abc");
    for (const value of store.dump().values()) expect(value).not.toContain(toHex(secret));
  });

  it("rejects a wrong passphrase", async () => {
    const sealed = await sealSecret(generateOwnerSecret(), PASS, "preview", FAST);
    await expect(openSecret(sealed, "wrong passphrase!!")).rejects.toThrow(/Wrong passphrase/);
  });

  it("binds the ciphertext to its network", async () => {
    const sealed = await sealSecret(generateOwnerSecret(), PASS, "preview", FAST);
    await expect(openSecret({ ...sealed, network: "mainnet" }, PASS)).rejects.toThrow();
  });

  it("refuses short passphrases and wrong-length secrets", async () => {
    await expect(sealSecret(generateOwnerSecret(), "short", "preview", FAST)).rejects.toThrow(/at least/);
    await expect(sealSecret(new Uint8Array(16), PASS, "preview", FAST)).rejects.toThrow(/32 bytes/);
  });

  it("keeps entries per network and contract, plus pending entries", async () => {
    const vault = new SecretVault(memoryStore());
    const sealed = await sealSecret(generateOwnerSecret(), PASS, "preview", FAST);
    vault.putPending(sealed, null);
    expect(vault.getPending("preview", null)).toEqual(sealed);
    const bound = vault.put(sealed, "c1");
    vault.clearPending("preview", null);
    expect(vault.getPending("preview", null)).toBeNull();
    expect(vault.get("preview", "c1")).toEqual(bound);
    expect(bound.contract_address).toBe("c1");
    expect(vault.get("preview", "c2")).toBeNull();
    expect(vault.get("mainnet", "c1")).toBeNull();
  });
});
