// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type BundleCheck, parseBundleFile } from "../../src/bundle.js";
import { isHex32 } from "../../src/hex.js";
import { type Verdict, verdict } from "../../src/verify.js";
import { isReceipt, readCase, readOnlyPublicData } from "./case-api.js";
import { config } from "./config.js";
import { FileDrop, KV, errorText } from "./ui.js";

export function VerifyView() {
  const [bundle, setBundle] = useState<BundleCheck | null>(null);
  const [address, setAddress] = useState("");
  const [claimedRevision, setClaimedRevision] = useState<string>("");
  const [result, setResult] = useState<Verdict | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalized = address.trim().toLowerCase();

  function onReceipt(text: string) {
    setResult(null);
    try {
      const r: unknown = JSON.parse(text);
      if (!isReceipt(r)) throw new Error("Not a Chaintrace attestation receipt");
      if (r.network !== config.networkId) throw new Error(`Receipt is for network ${r.network}, this page checks ${config.networkId}`);
      setAddress(r.contract_address);
      setClaimedRevision(r.revision);
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function verify() {
    if (!bundle) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const ledger = await readCase(readOnlyPublicData(), normalized);
      const expected = /^\d+$/.test(claimedRevision) ? BigInt(claimedRevision) : undefined;
      setResult(verdict(bundle, ledger, expected));
    } catch (err) {
      setError(`Could not read Midnight ledger: ${errorText(err)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>Verify a disclosed case bundle</h2>
        <p className="note">
          The bundle is hashed in this browser and compared with the latest commitment in the contract’s confirmed
          state, read from the {config.networkId} indexer. No wallet needed. Nothing is uploaded.
        </p>
        <FileDrop
          label="Drop the case bundle (.json)"
          onText={async (t) => {
            setResult(null);
            setBundle(await parseBundleFile(t));
          }}
        />
        {bundle && !bundle.ok && <p className="alert bad">{bundle.reason}</p>}
        {bundle?.ok && (
          <KV
            items={[
              ["Case", `#${String(bundle.bundle.case.id)} ${String(bundle.bundle.case.name ?? bundle.bundle.case.title ?? "")}`],
              ["Recomputed commitment", <span className="mono">{bundle.commitment}</span>],
            ]}
          />
        )}
        <FileDrop label="Optional: drop the attestation receipt to fill in the contract" onText={onReceipt} />
        <div className="grid2">
          <label>
            Contract address
            <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="64 hex characters" />
          </label>
          <label>
            Claimed revision (optional)
            <input type="text" value={claimedRevision} onChange={(e) => setClaimedRevision(e.target.value)} placeholder="e.g. 1" />
          </label>
        </div>
        <div className="row">
          <button className="btn primary" disabled={!bundle || !isHex32(normalized) || busy} onClick={verify}>
            {busy ? "Reading ledger…" : "Verify against Midnight"}
          </button>
        </div>
        {error && <p className="alert bad">{error}</p>}
      </section>

      {result?.status === "verified" && (
        <section className="verdict ok" aria-live="polite">
          <h2>Match: this is the attested version</h2>
          <KV
            items={[
              ["Contract", <span className="mono">{result.contractAddress}</span>],
              ["Revision", result.revision.toString()],
              ["Commitment", <span className="mono">{result.commitment}</span>],
              ["Contract code", "Verifier keys match this Chaintrace build"],
            ]}
          />
          <p className="note">
            The snapshot is byte-for-byte the version committed at this revision by the holder of the case owner
            secret. It does not prove the findings are correct.
          </p>
        </section>
      )}
      {result?.status === "failed" && (
        <section className="verdict fail" aria-live="polite">
          <h2>No match</h2>
          <p>{result.message}</p>
          <p className="note">Reason code: {result.reason}</p>
        </section>
      )}
    </div>
  );
}
