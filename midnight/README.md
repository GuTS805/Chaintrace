# Chaintrace Private Case Attestations (Midnight)

Privacy-first chain of custody for Chaintrace investigation cases. An investigator commits a salted hash of an exact case version to a Compact contract on Midnight. The case, its findings, wallet addresses and the investigator's identity never go on chain. Later, the investigator hands a reviewer the case bundle. The reviewer's browser recomputes the hash and compares it with the **confirmed** on-chain commitment.

**What a successful verification proves:** the disclosed snapshot is byte-for-byte the version committed at that revision, and whoever committed it held the case's private owner secret.

**What it does not prove:** that the findings or VASP attributions are true, who the investigator is in the real world, or that the evidence was authentic before it was committed.

## How it works

```text
Chaintrace case page                    Midnight DApp (this folder)                     Midnight (Preview)
--------------------                    ---------------------------                     ------------------
case JSON ──► canonical JSON + 32-byte salt ──► SHA-256 commitment ──► attest(rev, commitment) ──► case_commitment
             (bundle file, stays local)          owner_secret() witness ──► ZK proof ───────────► revision
                                                 (sealed in browser)                              owner_key
Reviewer:  bundle file ──► recompute hash ──► compare with confirmed ledger (indexer read, no wallet)
```

| Data | Where it lives |
| --- | --- |
| Case snapshot, findings, wallet addresses, officer name | Bundle file on the investigator's device; shared only with chosen reviewers |
| 32-byte salt | Inside the bundle; it hides the case from brute-force guessing of the commitment |
| Owner secret (32 bytes) | Browser only, AES-256-GCM sealed under a passphrase (PBKDF2-SHA256, 600k iterations); plaintext exists only in memory while a proof is generated |
| Public on chain | `case_commitment`, `revision`, `owner_key = persistentHash("chaintrace:case-owner:v1", secret)`, transaction metadata |

Trust boundary: the Chaintrace backend already stores case data. This feature keeps that data off the public chain and detects any later change to a shared snapshot. It does not hide case data from the Chaintrace server.

## Contract: [`contracts/private_case.compact`](contracts/private_case.compact)

One deployment per case. Compiler 0.31.1, language 0.23, compact-runtime 0.16.0 (ledger 8, the version used on Preview, Preprod and Mainnet).

| Circuit | Rule |
| --- | --- |
| `constructor()` | Takes the owner secret from the `owner_secret` witness and publishes only its domain-separated hash. Has no arguments, so the secret is never a public input. |
| `attest(expected_revision, commitment)` | Caller must hold the owner secret. `expected_revision` must equal the on-chain revision, so stale or replayed transactions fail. Rejects the empty commitment and re-attesting the current one. Guards against `Uint<32>` overflow. |
| `rotate_owner(new_owner_key)` | Caller must hold the current secret. Only the new secret's hash is passed in. The old secret stops working immediately. |
| `derive_owner_key(secret)` | Pure helper, shared by the contract and the DApp. |

Every exported circuit is a public entry point. Both state-changing circuits check ownership first.

## Repository layout

```text
contracts/          Compact source
src/                Shared TypeScript: bundle format, witness, vault, ledger read, verdict, tx stages
dapp/               Vite + React DApp (Attest, Verify, Owner key)
test/               Unit, simulator, UI and end-to-end tests (see below)
scripts/compile.mjs Compile with native `compact`, or through Docker on Windows
toolchain/          Dockerfile pinning Compact 0.31.1
```

## Setup

Requirements: Node.js 24.11+, Docker Desktop (for the compiler on Windows, the proof server and the E2E network).

```sh
cd midnight
npm install
npm run compile      # -> managed/private_case (contract JS, ZKIR, prover/verifier keys)
npm test             # unit + simulator + UI tests
npm run typecheck
```

`npm run compile` uses a native `compact` 0.31.1 if one is installed (Linux/macOS, via `compact update 0.31.1`). Otherwise it builds `toolchain/Dockerfile` and compiles inside the container. On Windows, the `compact.exe` on `PATH` is the NTFS compression tool, not the Midnight compiler.

### Tests

| Command | What runs | Needs |
| --- | --- | --- |
| `npm test` | Contract simulator (authorized, unauthorized, stale and replayed revision, duplicate and empty commitment, rotation, cross-case isolation); bundle canonicalization and the shared test vector; vault; verdict logic against real compiled verifier keys; transaction-stage ordering; DApp UI flows (jsdom) | Compiled contract |
| `npm run test:e2e` | Starts a local Midnight node, indexer and proof server in Docker, then runs the DApp's own code on a genesis-funded wallet: deploy, attest, verify, reject a forged attestation, revision 2 supersedes revision 1, owner rotation | Docker, about 3 min |
| `npm run test:smoke` | Reads the public Preview indexer | Internet |
| `npm run preview:run` | Attests a demo case on **Preview** with a headless wallet (saved in `.preview/`, gitignored), then verifies it as a reviewer would. On the first run it prints an address to fund once at https://faucet.preview.midnight.network; DUST registration is automatic. Each later run attests the next revision. | Proof server, funded wallet |

### Run the DApp against Preview

1. Start the proof server: `npm run proof-server` (image `midnightntwrk/proof-server:8.1.3`, port 6300, runs detached; `docker stop chaintrace-proof-server` stops it).
2. Copy `dapp/.env.example` to `dapp/.env`. The defaults target Preview.
3. Install the [Lace Midnight Preview](https://chromewebstore.google.com/detail/hgeekaiplokcnmakghbdfbgnlfheichg) extension (Chrome), switch it to **Preview**, and get tNIGHT from the Preview faucet (https://midnight-tmnight-preview.nethermind.dev/). The wallet generates DUST from tNIGHT to pay fees.
4. `npm run dev`, then open http://localhost:5173.
5. In Chaintrace, open a case. **Private attestation** downloads the bundle. **Attest on Midnight** opens this DApp. Set `NEXT_PUBLIC_MIDNIGHT_DAPP_URL` in the frontend if the DApp is hosted elsewhere.

### Investigator flow

1. Drop the bundle. The DApp re-checks that the bundle's hash is consistent.
2. Choose **New case contract** and set a passphrase. The DApp generates and seals the owner secret, deploys the contract, then attests revision 1. For a later version of the same case, choose **Existing contract** and unlock with the passphrase.
3. The stage tracker shows *proof generation → wallet balancing → prepared → submitted → confirmed*. "Confirmed" appears only after the finalized transaction has succeeded **and** a fresh ledger read shows the new commitment.
4. Download the receipt (contract address, revision, commitment, transaction hash, block; no case data) and back up the sealed owner secret.

### Reviewer flow

Open **Verify bundle**, drop the bundle (and optionally the receipt), then click **Verify against Midnight**. No wallet is needed. The check fails with a specific reason for:
- an altered case or wrong salt (`bundle-invalid` or `commitment-mismatch`)
- an unknown address (`contract-not-found`)
- a contract whose verifier keys differ from this build (`contract-code-mismatch`)
- an older revision that has been superseded (`superseded`)
- a contract with no attestation yet (`not-attested`)

Anyone can recompute a commitment without this code. It is SHA-256 over sorted-key, whitespace-free JSON of `{"case": <case with findings sorted by id>, "domain": "chaintrace-case-attestation-v1", "salt": <hex>}`. For example, in Python:

```python
import json, hashlib
b = json.load(open("bundle.json", encoding="utf-8"))
c = dict(b["case"])
if isinstance(c.get("findings"), list): c["findings"] = sorted(c["findings"], key=lambda f: f["id"])
doc = {"domain": b["format"], "salt": b["salt"], "case": c}
print(hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest())
```

`test/vectors/bundle-v1.json` is a fixed test vector. The TypeScript DApp, the Chaintrace frontend helper and the snippet above all produce `1791a389…270c` for it.

## Security notes and limitations

- **No recovery.** If the owner secret is lost (passphrase forgotten and no backup), the case can never be attested again; deploy a new contract. Use **Owner key → Rotate** if a passphrase or backup may have leaked.
- **Rotation is not instant revocation of past attestations.** Existing revisions stay valid. Rotation only stops future updates by the old secret.
- **Pending state is kept across interruptions.** The sealed secret is saved before a deploy or rotation is submitted, so closing the tab mid-transaction does not lose it. The Owner key tab can resolve a pending rotation against the chain.
- **Only the latest revision is on chain.** A reviewer can verify the current revision only. Bundles for earlier revisions are reported as `superseded`.
- **Contract maintenance key.** Midnight.js gives the deployer a contract maintenance key. This DApp keeps it in memory only, so once the page closes nobody holds a key that could replace the circuits. The reviewer's code check compares on-chain verifier keys with this build at every verification.
- **Browser storage.** The sealed secret sits in `localStorage` for this origin, separate from any case data. Clearing site data deletes it, so keep the downloaded backup.
- **What a match means.** A match shows integrity and possession of the owner secret, not correctness of the investigation (see the top of this document).
- Nothing in this DApp logs case data or secrets. Circuit arguments are only `expected_revision`, `commitment` and `new_owner_key`.

## License

Apache License 2.0 ([`LICENSE`](LICENSE)) for everything in `midnight/` and for `frontend/lib/case-attestation.ts`. Parts of `dapp/src/wallet.ts`, `dapp/src/private-state.ts` and `dapp/vite.config.ts` are adapted from `midnightntwrk/example-bboard` (Apache-2.0, Midnight Foundation). Pre-existing Chaintrace code is not relicensed by this folder.
