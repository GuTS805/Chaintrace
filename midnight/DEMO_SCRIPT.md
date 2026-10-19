# Demo video script (about 3 minutes)

For the Buildathon demo video. Record it on **Preview** with a real Lace wallet. If Lace is not set up, use the fallback at the end.

## Before recording

- [ ] `npm run proof-server` is running (port 6300).
- [ ] Lace is on **Preview**, funded with tNIGHT from the faucet, and has generated DUST.
- [ ] Chaintrace is running (`.\run.ps1`), with a demo case that has 2–3 findings.
- [ ] `cd midnight && npm run dev`; the DApp is open at http://localhost:5173.
- [ ] Browser zoom at 110–125%, notifications off.

## Shots

| # | Time | Screen | Say (roughly) |
| --- | --- | --- | --- |
| 1 | 0:00–0:15 | Chaintrace case page | “This is a crypto investigation case in Chaintrace: findings, suspect wallets, the investigator. When it’s handed to a supervisor or a court, nobody can prove it wasn’t edited. And we can’t publish it on a public chain.” |
| 2 | 0:15–0:30 | Click **Private attestation**; show the downloaded JSON briefly | “Chaintrace freezes this exact version: canonical JSON, a random salt and a SHA-256 commitment. The file stays on my machine.” |
| 3 | 0:30–0:45 | Click **Attest on Midnight**; drop the bundle in the DApp | “The Midnight DApp re-checks the bundle. Only this 32-byte commitment will go on chain.” |
| 4 | 0:45–1:25 | New case contract, passphrase, **Deploy contract and attest**; approve in Lace twice | “A random owner secret is generated and sealed in the browser. The contract checks it with a zero-knowledge witness, so only its hash is public. Watch the stages: proving locally, Lace balancing, prepared, submitted. It says confirmed only once the block is in and the ledger is re-read.” |
| 5 | 1:25–1:40 | Confirmed panel; **Download receipt**, **Back up sealed owner secret** | “Contract address, revision 1, the commitment and the transaction. The receipt has no case data.” |
| 6 | 1:40–2:10 | **Verify bundle** tab (or a second browser profile): drop bundle and receipt, **Verify** | “The reviewer needs no wallet. Their browser re-hashes the bundle and compares it with the confirmed on-chain state. It also checks that the contract runs our exact circuits. Match.” |
| 7 | 2:10–2:30 | Edit one finding in the JSON; verify again | “Change one word in a finding and it fails: commitment mismatch.” |
| 8 | 2:30–2:45 | Optional: attest a second revision, then verify the old bundle and show `superseded` | “A new version supersedes the old one, and the old bundle is reported as superseded, not as valid.” |
| 9 | 2:45–3:00 | Footer text of the DApp, or the deck’s “What a match means” slide | “This proves integrity and ownership, not that the findings are true. Code, tests and evidence are in the repo under Apache-2.0.” |

## After recording

Copy the contract address, transaction hash and verification result into `EVIDENCE.md` under a new “Preview run” heading, with the date.

## Fallback without Lace (about 2 minutes)

Uses the real Preview attestation recorded in `EVIDENCE.md`. No wallet is needed.

1. Chaintrace case page: show **Private attestation** and **Attest on Midnight**.
2. Terminal: show the end of `npm run preview:run` output (deploy, attest, `reviewer verdict: verified`).
3. DApp **Verify bundle** tab: drop `.preview/bundle-r1.json` and `.preview/receipt-r1.json`, then click **Verify against Midnight**. The result is a match.
4. Edit one finding in a copy of the bundle and verify again. The result is no match.
5. Close on the "what it proves" footer.
