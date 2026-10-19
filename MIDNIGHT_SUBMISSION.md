# Midnight Buildathon submission: Chaintrace Private Case Attestations

AKINDO WaveHack "Build Privacy-First Apps on Midnight", **2nd Wave** (building period 29 September – 19 October 2026).

## What was built this wave

Chaintrace is an existing wallet investigation and VASP attribution platform. This wave adds **privacy-first chain of custody on Midnight**. An investigator commits a salted hash of an exact case version to a Compact contract. The case, its findings, wallet addresses and the officer's identity stay off chain. A reviewer who is given the case bundle can verify, with no wallet, that it is exactly the attested version.

All Midnight code is new in this wave and licensed Apache-2.0 (`midnight/`):

- **Compact contract** (`midnight/contracts/private_case.compact`): owner secret from a private witness (never a public input, not even at deployment); `attest(expected_revision, commitment)` with stale/replay, duplicate and empty-commitment protection; `rotate_owner` for key rotation.
- **DApp** (`midnight/dapp`): Lace connection (DApp connector 4.x), deploy and attest with honest transaction states ("confirmed" only after the block and a fresh ledger read), reviewer verification against the confirmed ledger including a contract-code check, and a passphrase-sealed owner secret with backup, import and rotation.
- **Chaintrace integration**: deterministic case bundle export and an "Attest on Midnight" link on the case page.
- **Tests**: 42 unit, simulator and UI tests; a 6-case end-to-end suite on a local Midnight network with real proofs; a scripted Preview run.

## Live on Midnight Preview

Contract `8f2b54a3321ac1e7ce7d4aafbed276975c30a0939e0c8616f9dbb3dd44d11368`. Revision 1 was attested in block 1,364,229 and verified through the public indexer; an edited copy of the case was rejected. Details: `midnight/EVIDENCE.md`.

## What it proves, and what it does not

A match proves that the disclosed snapshot is byte-for-byte the committed version, and that the committer held the case owner secret. It does not prove that the findings are true, who the investigator is, or that evidence was authentic before it was committed.

## Try it

See `midnight/README.md` for setup, tests, the Preview run and the DApp walkthrough.

## Next wave

Selective disclosure of individual findings (Merkle commitments), delegated reviewer access recorded on chain, and many cases per contract.
