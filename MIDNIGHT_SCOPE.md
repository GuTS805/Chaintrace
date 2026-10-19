# Chaintrace Private Case Attestations — Project Scope

## 1. Product

Chaintrace ke investigation cases ke liye Midnight-based, privacy-first chain-of-custody feature. Investigator apne case ke ek exact version ka cryptographic commitment Midnight par record karega. Case details, findings, wallet addresses aur officer identity public ledger par nahi jayenge. Jab zaroorat ho, investigator reviewer ko case snapshot aur random salt dega; reviewer uska hash recompute karke confirmed on-chain commitment se match karega.

**Yeh kya prove karta hai:** disclosed snapshot wahi version hai jiska commitment record hua tha, aur us commitment ko update karne wale ke paas private owner secret tha.

**Yeh kya prove nahi karta:** case findings ya VASP attribution sach hain, investigator ki real-world identity kya hai, ya snapshot commit hone se pehle evidence authentic tha.

## 2. Target users and use case

- **Investigator:** case ko freeze/attest karta hai, later revision attest karta hai, aur selected reviewer ko evidence deta hai.
- **Reviewer/supervisor:** received snapshot ko Midnight par confirmed case commitment ke against verify karta hai.
- **Use case:** case handoff ya audit ke waqt yeh dikhana ki shared report attested version se badli nahi gayi.

## 3. MVP user flow

1. Officer Chaintrace mein authenticated case kholta hai aur **Prepare attestation** chunta hai.
2. Browser case snapshot ko deterministic format mein rakhta hai, 32-byte random salt banata hai, aur salted SHA-256 commitment nikalta hai. Browser sensitive bundle download karne deta hai.
3. Officer Midnight wallet connect karta hai. DApp private owner secret ko local private state se Compact witness mein deta hai aur `attest(commitment)` circuit call karta hai.
4. UI transaction ko `prepared`, `submitted`, aur `confirmed` states mein sahi tarah dikhata hai. Confirmation ke baad contract address, revision, commitment aur transaction reference dikhata hai.
5. Reviewer bundle upload karta hai; browser hash dobara banata hai, specified contract ka confirmed ledger state padhta hai, aur exact match/mismatch dikhata hai. Bundle server ko upload nahi hota.

## 4. MVP deliverables

| Area | Required outcome |
| --- | --- |
| Case snapshot | Deterministic versioned format; findings stable order mein; salt aur hash locally generate hon. |
| Compact contract | One case per deployment; public commitment + revision; private owner witness; unauthorized update reject; contract successfully compile ho. |
| Midnight integration | Wallet connection, deployment/call, proof generation, transaction confirmation, ledger read. |
| Verification | Local bundle validation plus **confirmed** ledger commitment comparison; wrong salt, modified case, wrong contract aur stale revision fail hon. |
| Security | Owner secret case data se alag secure local storage mein; no secret/case plaintext in public arguments or logs; explicit recovery/rotation limitation. |
| Quality | Contract simulation/tests, unauthorized-call test, valid update test, frontend flow test, documented setup. |
| Submission | Public GitHub repo, Apache-2.0 for new Midnight code, `midnightntwrk` GitHub topic, README, slide deck, demo video. |

## 5. Architecture and data boundary

```text
Chaintrace case API -> browser snapshot + salt -> SHA-256 commitment
                                      |                    |
                                      | private bundle     | public 32-byte value
                                      v                    v
                              investigator storage   Midnight Compact contract
                                      |                    |
                                      +---- reviewer -------+
                                           local compare with confirmed ledger state
```

- **Public on Midnight:** commitment, revision, owner-secret hash, transaction metadata.
- **Private:** full case, salt until intentionally disclosed, owner secret, any local witness state.
- **Trust boundary:** Chaintrace currently holds case data on its backend. This feature protects public-chain disclosure and detects later changes to a shared snapshot; it does not hide case data from the Chaintrace server.
- **Contract ownership:** one deployment per case for MVP. A later version can support multiple cases, delegated reviewer access, secret rotation and selective disclosure of individual findings.

## 6. Current implementation status (19 October 2026, end of day)

- **Contract:** hardened and compiled with Compact 0.31.1 (Docker image `midnight/toolchain`). Owner secret now comes from a witness in the constructor too (no constructor argument), domain-separated owner key, `expected_revision` stale/replay guard, duplicate and empty commitment rejection, `rotate_owner` circuit.
- **Tests:** 42 unit, simulator, UI and verify tests pass. The opt-in E2E test (6 cases) passes on a local Midnight network (node, indexer and proof server in Docker): deploy, attest, verify, forged attestation rejected, superseded revision, owner rotation. Record: `midnight/EVIDENCE.md`.
- **DApp:** `midnight/dapp` (Vite + React) covers Lace connection (DApp connector 4.x), deploy and attest with honest *proving → balancing → prepared → submitted → confirmed* stages, reviewer verification against the confirmed ledger with a contract-code check, and a passphrase-sealed owner secret with backup, import and rotation.
- **Chaintrace frontend:** canonical-JSON bundle export (same commitment as the DApp, shared test vector) and an "Attest on Midnight" link. Typecheck and `next build` pass.
- **Preview:** case contract `8f2b54a3…d11368` deployed, and revision 1 attested (block 1,364,229) and verified through the public indexer, using a headless wallet (`npm run preview:run`).
- **Not done:** the same flow in the browser with Lace, demo video, public repo and topic, AKINDO submission.
- **All of this is pre-Wave-3 work.** It still is not an eligible or submitted Buildathon entry.

## 7. Build sequence and completion criteria

1. Set up Node.js and Compact 0.31.1 with runtime 0.16.0; compile contract and fix any API/syntax issues. Save exact commands and output.
2. Run contract tests, add negative tests, and review every exported circuit for unauthorized callers and replay/overflow behavior.
3. Implement wallet + Midnight network integration, including deployment, proof generation, transaction submission, confirmation and ledger read.
4. Connect case-page export to the on-chain action; add local reviewer verification. No success message before confirmation.
5. Run end-to-end demo with one seeded case and record the contract address, revision, transaction and verification result.
6. Finish README, public repo/license/topic, pitch deck and demo video. Submit personally through AKINDO.

**Done means:** a fresh reviewer can follow the README, compile and run tests, attest a case on the target Midnight network, verify its bundle against confirmed contract state, and see altered data rejected.

## 8. Buildathon timing and constraints

AKINDO lists Wave 3 build period as **27 October–16 November 2026**. Existing code can be reused, but Midnight-related functionality evaluated for Wave 3 must be newly developed or materially extended during that wave. The prototype began before Wave 3 at the user's request; it alone is not sufficient. Confirm the precise deadline and current official rules before submission. Registration and entry must be performed personally; automated entries are prohibited.

Source: https://app.akindo.io/wave-hacks/jaMZjqPOBsLXvjdG
