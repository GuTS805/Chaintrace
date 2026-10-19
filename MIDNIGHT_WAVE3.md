# Chaintrace for Midnight Buildathon, Wave 3

## Fit and current status

Chaintrace is an existing wallet investigation and VASP attribution platform. It is a plausible starting point for a privacy-first investigative product: case notes, officer identity, and disclosure decisions are sensitive even when the underlying chain transfers are public. A Compact contract prototype and a local case-bundle export now exist, but the contract has not been compiled here and no transaction workflow is connected. This is not yet an eligible Midnight submission.

The proposed Wave 3 product is **Chaintrace Private Case Attestations**. An investigator keeps a case file and evidence off chain, publishes a commitment to a case snapshot on Midnight, and can later disclose a selected snapshot to an authorized reviewer who checks it against the on-chain commitment. The contract should enforce a useful authorization or disclosure rule using a private witness, not merely store a hash. A hash alone does not prove the investigation is correct; the UI and pitch must say so.

## Timing

- Current date used for this preparation: 19 October 2026 (India time).
- Pre-wave Chaintrace baseline commit: `1f3c13a2a66a6f7ee02bb24ce1e09550af4442c5`.
- Wave 2 build period has ended; Wave 3 build period is listed as 27 October–16 November 2026.
- A preliminary Midnight implementation began on 19 October at the user's request. The rules require Midnight-related functionality newly developed or materially extended during the applicable Wave, so this pre-wave work alone is insufficient for Wave 3. Record substantial new Wave 3 development separately.
- Confirm the exact Wave 3 deadline and official rules on AKINDO before submission; displayed dates may change.

## Proposed architecture

1. Chaintrace exports a canonical case snapshot containing case ID, investigation findings, evidence references, analyst ID, and version. Never put this plaintext or wallet-to-person mappings on the public ledger.
2. A client creates a random secret and commitment to the snapshot. Keep the secret and plaintext with the investigator. Document precisely which fields are public, private client state, and optional disclosures.
3. A Compact contract records the commitment and governs a meaningful private authorization or selective-disclosure action. The design must prevent an arbitrary caller from replacing or revealing someone else's case commitment. Review all exported circuits as public entry points.
4. A reviewer receives only the investigator-selected fields and sufficient proof or opening material to check the committed version. Clearly distinguish this from proof that the off-chain attribution is true.
5. Add an end-to-end UI path from an existing case to commitment, confirmation, and reviewer verification. The UI must show whether a transaction is simulated, submitted, or confirmed.

## Wave 3 build and evidence checklist

- [x] Pin the Compact compiler and runtime combination (0.31.1 / 0.16.0, matches the support matrix).
- [x] Implement at least one Compact contract with private-state management and a meaningful circuit; compile it successfully and save the exact command/output (`midnight/EVIDENCE.md`, pre-wave).
- [x] Add tests for unauthorized calls, mismatched commitments, replay or duplicate disclosure, and the valid disclosure path (simulator + local-network E2E, pre-wave).
- [ ] Integrate the generated contract with the case workflow and demonstrate one complete, accurately labelled path. Proven on a local network and on **Preview** (headless wallet, contract `8f2b54a3…d11368`); a browser run with Lace is still needed for the demo.
- [x] Update README with architecture, privacy boundaries, local setup, test instructions, and known limitations (`midnight/README.md`).
- [ ] Make Midnight-related code and code required to evaluate it public under Apache License 2.0. Check licensing of pre-existing code separately.
- [ ] Publish a public GitHub repository with the `midnightntwrk` topic/label.
- [ ] Prepare a slide deck and a demo video or video pitch; describe work completed during Wave 3.
- [ ] Register and submit personally through AKINDO; automated entries are prohibited. Confirm eligibility and exact deadline in the official rules.

## Sources

- Buildathon and rules: https://app.akindo.io/wave-hacks/jaMZjqPOBsLXvjdG
- Midnight documentation: https://docs.midnight.network/
- Private-state witnesses: https://docs.midnight.network/guides/private-state-witnesses
- Contract safety tutorial: https://docs.midnight.network/tutorials/battleship

Pre-wave status (19 October 2026): contract compiled, tests and local-network E2E passing, DApp built. See `midnight/EVIDENCE.md`. Wave 3 work must add or materially extend Midnight functionality after 27 October; candidates are listed in `MIDNIGHT_SCOPE.md` section 5 (multi-case contracts, delegated reviewer access, selective disclosure of individual findings).
