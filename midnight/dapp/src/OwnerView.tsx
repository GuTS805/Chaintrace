// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { isHex32, toHex } from "../../src/hex.js";
import {
  MIN_PASSPHRASE_LENGTH,
  generateOwnerSecret,
  isSealedSecret,
  openSecret,
  sealSecret,
} from "../../src/secret-vault.js";
import type { TxStage } from "../../src/tx-stages.js";
import { PrivateCase } from "../../src/contract.js";
import { buildProviders, readOnlyPublicData, rotateOwner } from "./case-api.js";
import { config } from "./config.js";
import { FileDrop, StageTracker, download, errorText, short } from "./ui.js";
import { vault } from "./vault.js";
import type { WalletConnection } from "./wallet.js";

async function onChainOwnerKey(address: string): Promise<string | null> {
  const state = await readOnlyPublicData().queryContractState(address);
  return state ? toHex(PrivateCase.ledger(state.data).owner_key) : null;
}

export function OwnerView({ wallet, onConnect }: { wallet: WalletConnection | null; onConnect: () => void }) {
  const [address, setAddress] = useState("");
  const [message, setMessage] = useState<{ kind: "good" | "bad" | "warn"; text: string } | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [next2, setNext2] = useState("");
  const [stage, setStage] = useState<TxStage>({ stage: "idle" });
  const [busy, setBusy] = useState(false);

  const a = address.trim().toLowerCase();
  const valid = isHex32(a);
  const stored = valid ? vault.get(config.networkId, a) : null;
  const pending = valid ? vault.getPending(config.networkId, a) : null;

  async function importBackup(text: string) {
    try {
      const parsed: unknown = JSON.parse(text);
      if (!isSealedSecret(parsed)) throw new Error("Not a sealed Chaintrace owner secret");
      if (parsed.network !== config.networkId) throw new Error(`Backup is for network ${parsed.network}`);
      const target = parsed.contract_address ?? a;
      if (!isHex32(target)) throw new Error("Enter the contract address first");
      vault.put(parsed, target);
      setAddress(target);
      setMessage({ kind: "good", text: "Sealed owner secret imported. It is still encrypted with its passphrase." });
    } catch (err) {
      setMessage({ kind: "bad", text: errorText(err) });
    }
  }

  async function checkKey() {
    if (!stored) return;
    setBusy(true);
    try {
      const secret = await openSecret(stored, current);
      const mine = toHex(PrivateCase.pureCircuits.derive_owner_key(secret));
      secret.fill(0);
      const chain = await onChainOwnerKey(a);
      setMessage(
        chain === mine
          ? { kind: "good", text: "Passphrase is correct and this secret is the current on-chain owner." }
          : { kind: "warn", text: "Passphrase is correct, but this secret is NOT the current on-chain owner." },
      );
    } catch (err) {
      setMessage({ kind: "bad", text: errorText(err) });
    } finally {
      setBusy(false);
    }
  }

  async function resolvePending() {
    if (!pending) return;
    setBusy(true);
    try {
      const secret = await openSecret(pending, next || current);
      const mine = toHex(PrivateCase.pureCircuits.derive_owner_key(secret));
      secret.fill(0);
      if ((await onChainOwnerKey(a)) === mine) {
        vault.put(pending, a);
        vault.clearPending(config.networkId, a);
        setMessage({ kind: "good", text: "The pending rotation is confirmed on chain. The new secret is now active." });
      } else {
        setMessage({ kind: "warn", text: "The pending rotation is not on chain. The previous secret is still the owner." });
      }
    } catch (err) {
      setMessage({ kind: "bad", text: errorText(err) });
    } finally {
      setBusy(false);
    }
  }

  async function rotate() {
    if (!wallet || !stored) return;
    setBusy(true);
    setMessage(null);
    let oldSecret: Uint8Array | null = null;
    const newSecret = generateOwnerSecret();
    try {
      oldSecret = await openSecret(stored, current);
      const sealedNew = await sealSecret(newSecret, next, config.networkId);
      vault.putPending(sealedNew, a);
      await rotateOwner(buildProviders(wallet), a, oldSecret, newSecret, setStage);
      vault.put(sealedNew, a);
      vault.clearPending(config.networkId, a);
      setMessage({ kind: "good", text: "Owner rotated. Back up the new sealed secret now; the old one no longer works." });
      setCurrent("");
      setNext("");
      setNext2("");
    } catch (err) {
      const text = errorText(err);
      setStage((s) => (s.stage !== "idle" ? { stage: "failed", error: text } : s));
      setMessage({ kind: "bad", text });
    } finally {
      oldSecret?.fill(0);
      newSecret.fill(0);
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>Owner secret for a case contract</h2>
        <label>
          Contract address
          <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="64 hex characters" />
        </label>
        {valid && (
          <p className="note">
            {stored ? "A sealed owner secret for this contract is stored in this browser." : "No owner secret for this contract in this browser."}
          </p>
        )}
        <div className="row">
          <button className="btn" disabled={!stored} onClick={() => stored && download(`chaintrace-owner-secret-${short(a, 6)}.json`, stored)}>
            Download sealed backup
          </button>
        </div>
        <FileDrop label="Import a sealed owner secret backup (.json)" onText={importBackup} />
        <p className="note">
          Backups stay encrypted with the passphrase. Keep one copy offline. Without the secret and passphrase, the
          case cannot be attested again, and there is no recovery.
        </p>
      </section>

      {stored && (
        <section className="card">
          <h2>Check or rotate</h2>
          <label>
            Current passphrase
            <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </label>
          <div className="row">
            <button className="btn" disabled={!current || busy} onClick={checkKey}>
              Check against chain
            </button>
          </div>
          <div className="grid2">
            <label>
              New passphrase (min {MIN_PASSPHRASE_LENGTH})
              <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
            </label>
            <label>
              Confirm new passphrase
              <input type="password" value={next2} onChange={(e) => setNext2(e.target.value)} autoComplete="new-password" />
            </label>
          </div>
          <p className="note">
            Rotation generates a new owner secret and moves ownership on chain. Use it if the passphrase or a backup may
            have been exposed. Only the new secret’s hash is published.
          </p>
          <div className="row">
            {!wallet && (
              <button className="btn small" onClick={onConnect}>
                Connect wallet
              </button>
            )}
            <button
              className="btn primary"
              disabled={!wallet || busy || !current || next.length < MIN_PASSPHRASE_LENGTH || next !== next2}
              onClick={rotate}
            >
              Rotate owner secret
            </button>
          </div>
          {stage.stage !== "idle" && <StageTracker title="Rotate owner" stage={stage} />}
          {pending && (
            <div className="alert warn">
              A rotation from an earlier session is pending.{" "}
              <button className="btn small" disabled={busy || !(next || current)} onClick={resolvePending}>
                Check it on chain
              </button>
              <span className="note"> Enter the new passphrase that rotation used.</span>
            </div>
          )}
        </section>
      )}
      {message && <p className={`alert ${message.kind}`}>{message.text}</p>}
    </div>
  );
}
