# Private case attestation prototype

This directory contains a Compact contract for one Chaintrace case per deployment. It stores a 32-byte case commitment and a revision counter. A 32-byte owner secret is supplied through a private witness; its hash is public, and the contract checks possession before every update. The case file and owner secret are never circuit arguments or ledger values. The owner secret must be generated and stored securely by the client; losing it prevents updates. A fresh secret must be used for every deployment.

The Chaintrace case page currently exports a local JSON bundle containing the complete case snapshot, random 32-byte salt, and SHA-256 commitment. **The bundle contains sensitive case data.** Store or share it only with an intended reviewer. Publishing the salt and bundle makes the case readable. The SHA-256 commitment can be passed as the `attest` argument after verifying the bundle locally. Do not interpret the hash as proof that the case findings are true.

## Build

Target: Compact compiler 0.31.1, language 0.23, compact runtime 0.16.0. Follow the official Windows/WSL installation guide if necessary. Then:

```sh
cd midnight
compact update 0.31.1
npm install
npm run compile
npm test
```

The generated `managed/` directory is build output and is ignored. A successful compile and test run is required before treating this as a Buildathon submission. This environment did not have Node.js, the Compact compiler, or working WSL access at implementation time, so compilation and the JavaScript test have **not** been verified here.

## Privacy and integration boundary

- Public: owner secret hash, latest commitment, revision, and transaction metadata.
- Private to the investigator: owner secret and exported case bundle.
- Off-chain verification: recompute `SHA-256(JSON.stringify({domain, salt, case}))` from the bundle, then compare it to a **confirmed** on-chain `case_commitment` read from the correct deployment. Self-consistency of the bundle alone proves nothing about who authored it.
- This prototype has no wallet connector, transaction submission, confirmation watcher, or independent reviewer UI yet. The case-page export is explicitly a preparation step, not an on-chain attestation.

The Midnight-related source in this directory and the case-attestation helper are licensed under Apache-2.0; see `LICENSE`. The pre-existing Chaintrace code has not been relicensed.
