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

> **Status: Phases 1–2 complete.** Later phases add bounded graph traversal (3),
> the signals + attribution engine (4), the frontend (5), and PDF reports (6).

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
