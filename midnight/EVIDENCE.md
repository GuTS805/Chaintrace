# Build and test evidence

Recorded 19 October 2026 (IST) on Windows 11, Node.js 24.19.0, Docker 29.8.2. Built during the Buildathon 2nd Wave (building period 29 September – 19 October 2026).

## Toolchain

| Component | Version | Source |
| --- | --- | --- |
| Compact compiler | 0.31.1 (language 0.23.0) | `toolchain/Dockerfile` via `compact update 0.31.1` |
| compact-runtime | 0.16.0 | npm |
| onchain-runtime-v3 | 3.0.0 (forced single copy, see `overrides` in `package.json`) | npm |
| midnight-js | 4.1.1 | npm |
| DApp connector API | 4.0.1 | npm |
| Proof server | 8.1.3 for Preview; 8.0.3 in the local E2E stack | Docker Hub |
| Local E2E stack | midnight-node 0.22.3, indexer-standalone 4.0.1 | `test/e2e/compose.yml` |

These match the Midnight support matrix for Preview, Preprod and Mainnet (ledger 8) as of this date.

## Compile

```text
$ npm run compile
$ docker run --rm -v ...\midnight:/work chaintrace-compact:0.31.1 compile contracts/private_case.compact managed/private_case
Compiling 2 circuits:
```

Output: `managed/private_case/{contract,zkir,keys,compiler}`, with prover and verifier keys for `attest` and `rotate_owner`.

## Tests

```text
$ npm run typecheck          -> OK
$ npm test
 Test Files  6 passed | 2 skipped (8)
      Tests  42 passed | 8 skipped (50)       # skipped = opt-in E2E and network suites
$ npm run test:e2e           # local Midnight node + indexer + proof server in Docker
 Test Files  1 passed (1)
      Tests  6 passed (6)     # ~150 s
$ npm run test:smoke         # public Preview indexer
      Tests  1 passed | 1 skipped (2)
$ npm run build              -> built (dapp/dist, keys and zkir copied)
$ (frontend) npx tsc --noEmit -> OK;  npx next build -> OK
```

## E2E on-chain record (local standalone network, `undeployed`)

The DApp's own `deployCase`, `attestCase` and `rotateOwner` code ran against a genesis-funded wallet through testkit's DApp-connector adapter, with real proofs:

| Event | Contract / commitment | Transaction | Block |
| --- | --- | --- | --- |
| deploy | `a115842dfb1e094c3b35ba592e6a3430c3f6007f1baa93fdd40262bcace1e393` | `48a41f16…9c1f7115` | 10 |
| attest r1 | `62ec7c0b…b08ed599` | `13844945…6aeedfed` | 13 |
| attest r2 | `fb59bc06…42543dea39` | `58cd4e1a…1ead224d5` | 16 |
| rotate_owner | n/a | `661a20e6…376bc9bd7` | 19 |

Assertions in the same run:
- The revision-1 bundle verified against the confirmed ledger.
- A tampered case and a wrong salt were rejected.
- An attestation with a random secret failed with `Unauthorized` and left the revision unchanged.
- After revision 2, the revision-1 bundle reported `superseded`.
- After rotation, the old secret failed and the new secret attested revision 3.
- An unknown address reported `contract-not-found`.

The local chain is discarded after the test, so these hashes cannot be looked up later. They show that the full path works.

## Preview run (public Midnight Preview network), 19 October 2026

`npm run preview:run`: a headless wallet-sdk wallet (not Lace), funded with 5,000 tNIGHT from https://faucet.preview.midnight.network. It then:
- registered for DUST (fee) generation
- deployed the case contract
- attested revision 1 of a demo case through the DApp's own `deployCase` / `attestCase`
- read the result back from the public Preview indexer as a reviewer would

| Event | Value |
| --- | --- |
| DUST registration tx | `00b99a01a0b06d8c1874659ce2f240383a9145be0faf747a88d8c4b7b0f32ccc33` |
| Contract address | `8f2b54a3321ac1e7ce7d4aafbed276975c30a0939e0c8616f9dbb3dd44d11368` |
| Deploy tx hash | `c51c563511ee16c5a0eef40e03c9a04b72e1e3964809c170c190d7aa9365e7b5`, block 1,364,225 |
| Attest r1 commitment | `62e24bdab34ac13ed6f4b4f1fe350976644634cd77387838888099b66a07be1c` |
| Attest r1 tx hash | `e718a14a0e7ca6e3ab7d27ca5e25f14faf9074f12ac93f4f598e594219cccc4f`, block 1,364,229 |
| Reviewer verdict (public indexer, no wallet) | `verified`, revision 1, contract code matched |
| Same bundle with the case edited | rejected (`bundle-invalid`) |

Anyone can re-check this: paste the contract address into the DApp's **Verify bundle** tab together with the bundle and receipt (kept locally in `midnight/.preview/`, not committed).

Wallet sync note: a brand-new Preview wallet took about 13.5 minutes to sync. testkit's own 90-second sync wait times out, so the script waits for the full sync itself.

## Not yet done (needs a person)

- **The same flow in the browser with Lace** (Midnight is built into the regular Lace extension), for the demo video.
- Demo video recording (script: `DEMO_SCRIPT.md`), public repository and AKINDO submission.
