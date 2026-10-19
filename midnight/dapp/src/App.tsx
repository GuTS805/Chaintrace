// Copyright 2026 Chaintrace contributors.
// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { config } from "./config.js";
import { type WalletConnection, connectWallet } from "./wallet.js";
import { primeWalletKeys } from "./case-api.js";
import { AttestView } from "./AttestView.js";
import { VerifyView } from "./VerifyView.js";
import { OwnerView } from "./OwnerView.js";
import { errorText } from "./ui.js";

type Tab = "attest" | "verify" | "owner";
const TABS: Array<[Tab, string]> = [
  ["attest", "Attest case"],
  ["verify", "Verify bundle"],
  ["owner", "Owner key"],
];

function initialTab(): Tab {
  const hash = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return hash === "verify" || hash === "owner" ? hash : "attest";
}

export function App() {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [wallet, setWallet] = useState<WalletConnection | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [walletError, setWalletError] = useState<string | null>(null);

  useEffect(() => {
    const onHash = () => setTab(initialTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  async function connect() {
    setConnecting(true);
    setWalletError(null);
    try {
      const w = await connectWallet(config.networkId);
      await primeWalletKeys(w);
      setWallet(w);
    } catch (err) {
      setWalletError(errorText(err));
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <div className="brand-mark" aria-hidden />
          <div>
            <h1>Chaintrace Case Attestations</h1>
            <p className="sub">Private chain-of-custody commitments on Midnight</p>
          </div>
        </div>
        <div className="row">
          <span className="pill info">Network: {config.networkId}</span>
          {wallet ? (
            <span className="pill good">Wallet connected</span>
          ) : (
            <button className="btn small" onClick={connect} disabled={connecting}>
              {connecting ? "Connecting…" : "Connect wallet"}
            </button>
          )}
        </div>
      </header>
      {walletError && <p className="alert bad" style={{ marginBottom: 16 }}>{walletError}</p>}

      <nav className="tabs" role="tablist">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            role="tab"
            className="tab"
            aria-selected={tab === id}
            onClick={() => {
              window.location.hash = `/${id}`;
              setTab(id);
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "attest" && <AttestView wallet={wallet} onConnect={connect} />}
      {tab === "verify" && <VerifyView />}
      {tab === "owner" && <OwnerView wallet={wallet} onConnect={connect} />}

      <footer className="note" style={{ marginTop: 32 }}>
        An attestation proves that a disclosed snapshot is the exact version committed on chain, and that the
        committer held the case owner secret. It does not prove that the findings or attributions are true, who
        the investigator is, or that evidence was authentic before it was committed.
      </footer>
    </div>
  );
}
