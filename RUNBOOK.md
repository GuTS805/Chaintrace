# ChainTrace — Judge Runbook

**What it does:** paste an unknown wallet address → get the likely **exchange (VASP)** behind it, with a **calibrated confidence score** and a **traceable evidence chain** — or an honest **"insufficient evidence."** No LLM in the attribution path.

---

## 1. Start (one command)

From the project root in **PowerShell**:

```powershell
.\run.ps1
```

It sets up the backend (SQLite — no Docker), applies migrations, seeds the demo,
starts the API + frontend in their own windows, and opens the browser at
**http://localhost:3000** when you see **READY**.

Stop everything: `.\run.ps1 -Stop`

> First run installs dependencies (a few minutes). After that it's seconds.
> Needs Python 3.11+ and Node.js on the machine.

---

## 2. The 90-second demo flow

```
Unknown wallet → Investigate → Graph → Attribution → WHY? → Risk → Case → PDF
```

1. **Unknown wallet** — On the home page, open **CASE-01 · Ransomware → exchange**
   (or paste its address into `trace>`).
2. **Investigate** — The wallet page loads attribution, risk, and the graph together.
3. **Graph** — Right panel: the money flow. Root wallet is **amber**, the exchange
   is **violet**. *"We traced the funds hop-by-hop; click any node to pivot."*
4. **Attribution** — Top instrument: **Binance ~99.5%**, with the bar showing the
   **calibrated probability** and a tick at the **0.55 threshold**.
5. **WHY?** — The **evidence chain** below is the whole point. Each signal
   (deposit sweep, temporal correlation, known label, pattern, hop path) shows a
   plain-English reason, the transactions behind it, and its **contribution** to
   the score. *"Every number traces to on-chain evidence — nothing is a black box."*
6. **Risk** — Separate panel: **MEDIUM**, flagging the **sanctioned Tornado Cash**
   mixer upstream. *"Risk and attribution are different questions; we keep them
   separate on purpose."*
7. **Case** — Pick a case in the **Case** panel and **attach** the wallet
   (create one first under **cases** if empty).
8. **PDF** — Click **↓ report (PDF)** (top of the wallet page, or on a case) for a
   one-click investigator report: verdict, full evidence chain, risk, and a graph
   snapshot.
9. **SAHYOG request** — On an attributed wallet, click **⚖ disclosure request
   (SAHYOG)** for a ready lawful information-request draft addressed to the
   attributed VASP (KYC, bank/UPI, IP logs, beneficial owner, freeze) — the actual
   next step an I4C/LEA officer files. *"We don't just name the exchange, we hand
   the officer the request to send it."*

**Stablecoin note:** live traces also pull **ERC-20 (USDT/USDC)** transfers — the
graph labels each edge's asset, so stablecoin laundering is traced too.

**The live "any wallet" moment (big one):** paste **any real Ethereum address**
into `trace>`. If it isn't cached, a **⚡ Fetch from Ethereum (live)** panel
appears → click it → we pull the wallet's transactions live from Blockscout and
run the same pipeline on it. *"It's not canned — any real wallet, traced live."*
(Needs internet; the six seeded cases stay fully offline as the reliable spine.)

**The "I don't know" moment (do this one):** open **CASE-03 · No VASP linkage** →
it returns **INSUFFICIENT EVIDENCE**, not a forced guess. Then **CASE-04 · Two
exchanges** → **AMBIGUOUS**, two credible candidates split. *"A tool law
enforcement can trust knows when to abstain."*

---

## 3. The demo cases

Four synthetic cases exercise model behaviour; two **genuine** mainnet wallets
(captured from Blockscout) prove the same pipeline runs on real data.

| Case | Address ends… | Result | Point it proves |
|---|---|---|---|
| CASE-01 Ransomware → exchange | `…36edc3` | Binance ~99% | clean, high-confidence attribution + full evidence |
| CASE-02 Peel chain | `…f95b3f` | Kraken (confident) | traced to Kraken across a 5-hop peel chain |
| CASE-03 No VASP linkage | `…766772` | **insufficient** | the system abstains instead of guessing |
| CASE-04 Two exchanges | `…f07a17` | **ambiguous** | split verdict when no candidate dominates |
| CASE-05 Real wallet — Kraken | `…8ad09b` | Kraken | **real** Ethereum wallet; deposit verifiable on-chain |
| CASE-06 Real wallet — Binance | `…99081c` | Binance ~0.76 | **real** wallet, second VASP, moderate confidence |

> CASE-05/06 are real mainnet wallets. Say: *"Same pipeline, real Ethereum data —
> and you can verify the deposit transaction yourself on any explorer."*

---

## 4. Why it's different (talking points)

- **Explainable, not a chatbot.** Attribution = heuristics + a calibrated
  gradient-boosted classifier. Every score decomposes into named evidence signals
  (contributions from TreeSHAP).
- **Calibrated probabilities.** 99% means ~99% — validated (Brier 0.074), curve in
  `backend/models/calibration_curve.png`.
- **Knows when to stop.** `insufficient_evidence` and `ambiguous` are first-class
  outcomes.
- **Deposit-sweep detection** (many deposit addresses → one hot wallet) is a
  first-class signal, stronger than raw hop distance.
- **Bounded, auditable traversal** (recursive SQL, max hops / value / nodes) with a
  reported reason whenever it prunes.
- **Risk ≠ attribution** — computed independently.

---

## 5. If something goes wrong

- **Browser shows "Tracing…" then an error** → the API window may still be
  compiling; refresh after a few seconds. Check http://localhost:8000/health.
- **Port already in use** → `.\run.ps1 -Stop`, then `.\run.ps1` again.
- **Nothing starts** → confirm `python --version` (3.11+) and `npm --version` work,
  then run `.\run.ps1 -Fresh`.
- **Re-seed / reset data** → delete `backend\chaintrace.db` and run `.\run.ps1`.

---

## 6. Honest scope (say it if asked)

- The model is calibrated on our **synthetic scenario generator** — stated plainly,
  not implied as real-chain calibration.
- The pipeline is **real-chain-ready** (Etherscan-schema importer); we deliberately
  don't depend on live high-degree hot-wallet traversal during the demo for
  reliability.
