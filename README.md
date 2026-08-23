# VASP Attribution & Investigation Platform

Attribute an unknown wallet address to a likely **VASP** (Virtual Asset Service
Provider / exchange) with a **calibrated confidence score** and a
**human-readable evidence chain**. Built for SIH problem statement 26182
(law-enforcement crypto tracing).

The differentiator is **explainability**. There is no LLM in the core
attribution path — attribution is heuristics + a gradient-boosted classifier
(calibrated), and every score traces to concrete on-chain evidence. The system
can also explicitly say **"insufficient evidence"** rather than force-attribute
every wallet.

> **Status: all six phases complete.**

## Run the demo (one command, Windows)

```powershell
.\run.ps1        # setup if needed, start API + frontend (SQLite, no Docker), open the browser
.\run.ps1 -Stop  # stop both servers
```

See **[RUNBOOK.md](RUNBOOK.md)** for the 90-second judge walkthrough
(unknown wallet → graph → attribution → why → risk → case → PDF).

## Real-chain ready

The pipeline consumes the standard **Etherscan `txlist` schema**, so traversal +
attribution run on real data unchanged — demonstrated offline, without depending
on live hot-wallet traversal:

```bash
make import-realchain          # replay the bundled Etherscan-schema sample
# or snapshot a real low-degree wallet once (needs ETHERSCAN_API_KEY), then replay offline:
python -m app.ingest.chain_import --address 0x... --save data/realchain/case.json
python -m app.ingest.chain_import --file data/realchain/case.json
```

## Reports (Phase 6)

One-click investigator PDFs, generated server-side with reportlab (pure Python,
offline — no headless browser):

- `GET /wallets/{addr}/report` — verdict, candidates, **full evidence chain with
  per-signal contributions**, independent risk section, and a drawn
  transaction-graph snapshot.
- `GET /cases/{id}/report` — case summary, investigator, and all findings/notes.

The frontend exposes a **↓ report (PDF)** button on the wallet and case pages.

## Frontend (Phase 5)

Next.js 14 (App Router) + TypeScript + Tailwind + React Flow. Dark, dense,
terminal-adjacent, data-first. Verified end-to-end against the live API.

- `/` — wallet search + offline demo wallets
- `/wallets/{address}` — attribution panel (probability bars + expandable
  evidence with per-signal TreeSHAP contributions), independent risk panel,
  React Flow transaction graph (root/VASP/mixer nodes colour-coded, click a node
  to trace it), and attach-to-case
- `/cases`, `/cases/{id}` — create cases, attach wallets, add findings/notes

The backend gained a small cases API (`/cases…`) and CORS. Run:

```bash
cd frontend && npm install && cp .env.example .env.local && npm run dev
```

## Graph traversal + path extraction (Phase 3)

Bounded multi-hop traversal via a single `WITH RECURSIVE` CTE (verified to render
on both Postgres and SQLite), cycle-free through a path string carried in the
recursion. Every traversal is bounded and reports exactly why it stopped.

- `SqlGraphRepository` (behind the `GraphRepository` interface) — `traverse()`
  and `shortest_paths()`.
- `TraversalBounds`: `max_hops`, `min_value_wei`, `since`/`until`, `max_nodes`,
  and `direction` (FORWARD / REVERSE / BOTH — REVERSE powers deposit-sweep).
- `PruneInfo` reports `pruned` + concrete `reasons` (`MAX_HOPS`, `MAX_NODES`,
  `MIN_VALUE`, `TIME_WINDOW`) — each detected with a bounded EXISTS check so the
  flag is honest, never a guess.

Endpoints:

```
GET /wallets/{addr}/graph?depth=&min_value=&since=&until=&direction=&max_nodes=
    -> { root, nodes[], edges[], prune }

GET /wallets/{addr}/paths-to-labeled?depth=&direction=&limit_per_target=
    -> [ { target, label_name, vasp_name, shortest_hops, paths[][] } ]
```

## Demo scenarios (Phase 2)

Four deterministic, fully offline scenarios — these *are* the demo. Each
exercises one attribution outcome. `make seed-demo` loads them (and the bundled
real labels) into the DB with zero network access; re-running is idempotent.

| Scenario | Unknown wallet resolves to | Expected outcome |
|---|---|---|
| `ransomware_to_exchange` | Binance (deposit-sweep) | **CLEAN** (~90%+) |
| `peel_chain` | Kraken (5-hop peel) | **MODERATE** (~70%) |
| `dead_end` | — (no VASP linkage) | **INSUFFICIENT** ("I don't know") |
| `two_exchanges` | Binance vs Coinbase | **AMBIGUOUS** (split) |

The generator (`app/synthetic/`) is deterministic (stable addresses/hashes/
timestamps) and doubles as the Phase 4 classifier's labeled training data: every
scenario declares its `unknown_wallet`, `ground_truth` VASP (or `None`), and the
`expected` outcome. `build_fixture_provider()` turns the same scenarios into an
offline `ChainProvider` for tests and later phases.

## Stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async)
- **DB:** PostgreSQL (app + transaction store), Redis cache. Graph traversal via
  recursive CTEs in Postgres, behind a `GraphRepository` interface (Neo4j-swappable).
- **ML (Phase 4):** scikit-learn + XGBoost with `CalibratedClassifierCV`.
- **Frontend (Phase 5):** Next.js 14 (App Router), TypeScript, Tailwind, React Flow.

## Phase 1 — what's here

```
backend/
  app/
    config.py            # Pydantic settings from env
    enums.py             # shared domain enums (incl. Evidence SignalType)
    logging.py           # structlog config
    main.py              # FastAPI app (+ /health)
    db/                  # async engine/session + declarative base
    models/              # wallets, transactions, labels, vasps,
                         #   clusters(+members), cases, findings
    schemas/             # AttributionResult / Evidence (hard req #1, #2),
                         #   GraphResult / PruneInfo (hard req #5)
    repositories/        # GraphRepository interface + TraversalBounds
    providers/           # ChainProvider protocol + offline FixtureProvider
    ingest/              # offline label ingestion (idempotent)
    cache/               # Redis JSON cache (degrades gracefully)
  alembic/               # async migrations (initial schema committed)
  data/labels/           # bundled offline label sources
  tests/                 # pytest, offline (SQLite), no network
docker-compose.yml       # postgres + redis
```

### Design decisions carried forward from the spec review

- **Synthetic generator does double duty (Phase 2):** it produces both the demo
  fixtures *and* the classifier's labeled training data. This means Phase 4's
  reported calibration curve / Brier score are measured against the synthetic
  distribution — the README will state that plainly rather than imply real-chain
  calibration.
- **Calibration (Phase 4):** train both isotonic and sigmoid, pick by holdout
  Brier. Isotonic overfits at small N; we won't hard-commit to it.
- **`insufficient_evidence` vs `ambiguous` are distinct states.** No candidate
  above the floor → `insufficient_evidence`. Multiple credible candidates, none
  dominant → `ambiguous` (two split candidates, *not* "I don't know"). Both are
  first-class fields on `AttributionResult`.
- **Deposit-sweep detection needs reverse traversal.** Consolidation is a
  property of a candidate hot wallet's *inbound* edges, so `TraversalBounds`
  carries a `direction` (FORWARD / REVERSE / BOTH).
- **Phase 1 ships one offline provider.** The live Etherscan/RPC provider +
  failover are deferred — they are not on the offline demo path, and live data
  against a real hot wallet is a demo-reliability risk.
- **Risk score and VASP attribution stay separate** (different questions;
  conflating them is a correctness bug).

## Signals + attribution engine (Phase 4)

Six signals, each a small class with a common interface, emit one classifier
feature **and** a human-readable `Evidence` object. The expensive graph
derivations run once in `build_graph_facts`, so training and inference compute
features identically (no train/serve skew).

| Signal | Feature | What it measures |
|---|---|---|
| `HOP_PATH` | hop_closeness | shortest-path proximity to the candidate |
| `DEPOSIT_SWEEP` | sweep_intensity | many→one consolidation into the hot wallet |
| `COUNTERPARTY_OVERLAP` | counterparty_overlap | shared associates with the deposit cluster |
| `TEMPORAL_CORRELATION` | temporal_correlation | deposit timing vs sweep timing |
| `KNOWN_LABEL` | label_confidence | reaches a labeled wallet (× source confidence) |
| `PATTERN_SIMILARITY` | pattern_similarity | cosine to a canonical exchange fingerprint |

Pipeline: `feature_vector` → **XGBoost** → **isotonic/sigmoid calibration** (the
lower-Brier of the two on a held-out split is kept). Per-prediction feature
contributions come from XGBoost's built-in **TreeSHAP** (`pred_contribs`) and set
each Evidence's `weight`. Hop distance is a *feature*, never a hard-coded
confidence (requirement #4).

**Calibration report** (held-out test, `make train`, seed 42):

| calibration | Brier score |
|---|---|
| uncalibrated | 0.075 |
| **isotonic (chosen)** | **0.074** |
| sigmoid | 0.078 |

Splits: 3600 train / 1200 calib / 1200 test; positive rate 0.61. Calibration
curve: `backend/models/calibration_curve.png`.

> **Honesty note (from the spec review):** the classifier is trained on the
> synthetic generator (`app/synthetic/training.py`), with labels drawn from an
> explicit logistic ground truth over the features — so the Brier score and
> calibration curve measure calibration against that synthetic distribution, not
> real-chain data. This is stated plainly rather than implied otherwise.

The engine assembles calibrated candidates + evidence into `AttributionResult`
and decides the outcome: a dominant candidate above threshold → single
attribution; two close credible candidates → **ambiguous**; nothing above the
floor → **insufficient_evidence**. Demo behaviour:

| Scenario | Result | Detail |
|---|---|---|
| ransomware_to_exchange | single | Binance ~0.99 (risk MEDIUM: upstream mixer) |
| peel_chain | single | Kraken ~0.64 (moderate) |
| dead_end | insufficient_evidence | no candidate cleared the floor |
| two_exchanges | ambiguous | Binance vs Coinbase, split |

**Risk is computed separately** from attribution (`app/attribution/risk.py`) —
exposure to sanctioned/mixer/scam entities by proximity in *both* directions —
because risk and VASP attribution are different questions.

Endpoints:

```
GET /wallets/{addr}/attribution?depth=  -> AttributionResult (candidates+evidence)
GET /wallets/{addr}/risk?depth=         -> RiskResult (score, level, indicators)
```

The trained model artifact is committed under `backend/models/` so the demo runs
without retraining; regenerate with `make train`.

## Quickstart

```bash
# 1. install backend deps (into a venv)
cd backend && python -m pip install -e ".[dev]"

# 2. start postgres + redis
docker-compose up -d           # from repo root

# 3. copy env and apply migrations
cp .env.example .env
cd backend && alembic upgrade head

# 4. load bundled labels (offline)
python -m app.ingest.labels

# 5. run the API
uvicorn app.main:app --reload  # http://localhost:8000/health
```

A `Makefile` wraps these (`make install`, `make up`, `make migrate`,
`make ingest-labels`, `make dev`).

## Verify (offline, no docker required)

```bash
cd backend
python -m pytest -q      # 15 tests, in-memory SQLite
ruff check .             # lint
mypy                     # strict type-check on app/
```

## Hard requirements (tracked)

1. **Structured evidence, not just a number** — `schemas/attribution.py`.
2. **Can say "I don't know"** — `insufficient_evidence` on `AttributionResult`.
3. **Deposit-sweep is first-class** (Phase 4; reverse traversal supported now).
4. **No hard-coded confidence percentages** — hop distance etc. are model
   features (Phase 4), never lookup tables.
5. **Bounded traversal** — `TraversalBounds` + `PruneInfo` (`pruned` + reasons).

## Notes

- Python is pinned to **3.11** for deployment (Render); local dev on 3.13 works.
- The initial Alembic migration was generated offline; it uses portable
  SQLAlchemy types and applies on both Postgres and SQLite. Regenerate against
  Postgres with `make revision m="..."` if you prefer PG-native rendering.
- Real `.env` is gitignored; `.env.example` is committed.
