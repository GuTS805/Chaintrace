# Build and test evidence

Recorded 19 October 2026 (IST) on Windows 11, Node.js 24.19.0, Docker 29.8.2. **This is pre-Wave-3 work.** The Wave 3 build period is 27 October–16 November 2026. Record new runs here for work done during the wave.

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

## Not yet done (needs a person)

- **Preview deployment with a real Lace wallet.** This needs Lace and tNIGHT from the Preview faucet, which uses a human check. Record the contract address, transaction hash and verification result here once done.
- Demo video recording (script: `DEMO_SCRIPT.md`), public repository and AKINDO submission.
