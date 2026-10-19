// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type BundleCheck, parseBundleFile } from "../../src/bundle.js";
import { isHex32 } from "../../src/hex.js";
import { MIN_PASSPHRASE_LENGTH, generateOwnerSecret, openSecret, sealSecret } from "../../src/secret-vault.js";
import type { TxStage } from "../../src/tx-stages.js";
import { type AttestationReceipt, attestCase, buildProviders, deployCase, makeReceipt } from "./case-api.js";
import { config } from "./config.js";
import { FileDrop, KV, StageTracker, download, errorText, short } from "./ui.js";
import { recallContract, rememberContract, vault } from "./vault.js";
import type { WalletConnection } from "./wallet.js";

type Mode = "new" | "existing";

export function AttestView({ wallet, onConnect }: { wallet: WalletConnection | null; onConnect: () => void }) {
  const [bundle, setBundle] = useState<BundleCheck | null>(null);
  const [mode, setMode] = useState<Mode>("new");
  const [address, setAddress] = useState("");
  const [pass, setPass] = useState("");
  const [pass2, setPass2] = useState("");
  const [deployStage, setDeployStage] = useState<TxStage>({ stage: "idle" });
  const [attestStage, setAttestStage] = useState<TxStage>({ stage: "idle" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<AttestationReceipt | null>(null);

  const caseId = bundle?.ok ? bundle.bundle.case.id : null;
  const normalized = address.trim().toLowerCase();

  async function onBundle(text: string) {
    setReceipt(null);
    setError(null);
    setDeployStage({ stage: "idle" });
    setAttestStage({ stage: "idle" });
    const check = await parseBundleFile(text);
    setBundle(check);
    if (check.ok) {
      const known = recallContract(config.networkId, check.bundle.case.id);
      if (known) {
        setMode("existing");
        setAddress(known);
      }
    }
  }

  const passOk =
    mode === "new" ? pass.length >= MIN_PASSPHRASE_LENGTH && pass === pass2 : pass.length > 0 && isHex32(normalized);
  const canRun = !!wallet && !!bundle?.ok && passOk && !busy;

  async function run() {
    if (!wallet || !bundle?.ok) return;
    setBusy(true);
    setError(null);
    setReceipt(null);
    const providers = buildProviders(wallet);
    let secret: Uint8Array | null = null;
    let deploySubmitted = false;
    try {
      let target = normalized;
      if (mode === "new") {
        secret = generateOwnerSecret();
        const sealed = await sealSecret(secret, pass, config.networkId);
        // Persist before submitting so the secret survives a closed tab mid-deploy.
        vault.putPending(sealed, null);
        const deployed = await deployCase(providers, secret, (s) => {
          if (s.stage === "submitted") deploySubmitted = true;
          setDeployStage(s);
        });
        target = deployed.contractAddress;
        vault.put(sealed, target);
        vault.clearPending(config.networkId, null);
        rememberContract(config.networkId, bundle.bundle.case.id, target);
        setMode("existing");
        setAddress(target);
      } else {
        const sealed = vault.get(config.networkId, target);
        if (!sealed) throw new Error("No owner secret for this contract in this browser. Import a backup on the Owner key tab.");
        secret = await openSecret(sealed, pass);
      }

      const result = await attestCase(providers, target, secret, bundle.commitment, setAttestStage);
      const r = makeReceipt(config.networkId, target, bundle.bundle.case.id, result.ledger, result.confirmation);
      setReceipt(r);
      setPass("");
      setPass2("");
    } catch (err) {
      const message = errorText(err);
      setError(message);
      if (mode === "new" && !deploySubmitted) vault.clearPending(config.networkId, null);
      setDeployStage((s) => (s.stage !== "idle" && s.stage !== "confirmed" ? { stage: "failed", error: message } : s));
      setAttestStage((s) => (s.stage !== "idle" && s.stage !== "confirmed" ? { stage: "failed", error: message } : s));
    } finally {
      secret?.fill(0);
      setBusy(false);
    }
  }

  function backup() {
    const sealed = vault.get(config.networkId, normalized);
    if (sealed) download(`chaintrace-owner-secret-${short(normalized, 6)}.json`, sealed);
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>1. Case bundle</h2>
        <p className="note">
          Export it from the Chaintrace case page (“Private attestation”). The bundle contains the full case and its
          salt. It stays on this device; only its 32-byte commitment goes on chain.
        </p>
        <FileDrop label="Drop the case bundle (.json) or click to choose" onText={onBundle} />
        {bundle && !bundle.ok && <p className="alert bad">{bundle.reason}</p>}
        {bundle?.ok && (
          <KV
            items={[
              ["Case", `#${String(bundle.bundle.case.id)} ${String(bundle.bundle.case.name ?? bundle.bundle.case.title ?? "")}`],
              ["Findings", String(bundle.bundle.case.findings?.length ?? 0)],
              ["Created", bundle.bundle.created_at],
              ["Commitment", <span className="mono">{bundle.commitment}</span>],
            ]}
          />
        )}
      </section>

      <section className="card">
        <h2>2. Case contract and owner secret</h2>
        <div className="row">
          <label className="radio">
            <input type="radio" checked={mode === "new"} onChange={() => setMode("new")} /> New case contract
          </label>
          <label className="radio">
            <input type="radio" checked={mode === "existing"} onChange={() => setMode("existing")} /> Existing
            contract (new revision)
          </label>
        </div>
        {mode === "existing" && (
          <label>
            Contract address
            <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="64 hex characters" />
          </label>
        )}
        <div className="grid2">
          <label>
            {mode === "new" ? `New passphrase (min ${MIN_PASSPHRASE_LENGTH} characters)` : "Passphrase"}
            <input type="password" value={pass} onChange={(e) => setPass(e.target.value)} autoComplete="new-password" />
          </label>
          {mode === "new" && (
            <label>
              Confirm passphrase
              <input type="password" value={pass2} onChange={(e) => setPass2(e.target.value)} autoComplete="new-password" />
            </label>
          )}
        </div>
        <p className="note">
          {mode === "new"
            ? "A random owner secret is generated, sealed with this passphrase, and stored in this browser. It never leaves the device. There is no recovery: back it up after deployment."
            : "Unlocks the sealed owner secret for this contract. Only its hash is on chain."}
        </p>
      </section>

      <section className="card">
        <h2>3. Attest on Midnight</h2>
        {!wallet && (
          <div className="row">
            <p className="note">Connect Lace on Preview. Fees are paid in DUST, which the wallet generates from tNIGHT (Preview faucet). Run the proof server locally.</p>
            <button className="btn small" onClick={onConnect}>
              Connect wallet
            </button>
          </div>
        )}
        <div className="row">
          <button className="btn primary" disabled={!canRun} onClick={run}>
            {busy ? "Working…" : mode === "new" ? "Deploy contract and attest" : "Attest new revision"}
          </button>
        </div>
        {deployStage.stage !== "idle" && <StageTracker title="Deploy case contract" stage={deployStage} />}
        {attestStage.stage !== "idle" && <StageTracker title="Attest commitment" stage={attestStage} />}
        {error && attestStage.stage === "idle" && deployStage.stage === "idle" && <p className="alert bad">{error}</p>}
      </section>

      {receipt && (
        <section className="verdict ok" aria-live="polite">
          <h2>Confirmed on Midnight</h2>
          <KV
            items={[
              ["Contract", <span className="mono">{receipt.contract_address}</span>],
              ["Revision", receipt.revision],
              ["Commitment", <span className="mono">{receipt.commitment}</span>],
              ["Transaction", <span className="mono">{receipt.txHash}</span>],
              ["Block", String(receipt.blockHeight)],
            ]}
          />
          <div className="row">
            <button
              className="btn"
              onClick={() => download(`chaintrace-case-${String(caseId)}-receipt-r${receipt.revision}.json`, receipt)}
            >
              Download receipt
            </button>
            <button className="btn" onClick={backup}>
              Back up sealed owner secret
            </button>
          </div>
          <p className="note">
            Give a reviewer the case bundle and the receipt. The receipt holds no case data. Sharing the bundle
            discloses the full case.
          </p>
        </section>
      )}
    </div>
  );
}
