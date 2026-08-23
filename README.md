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

## Provider layer (Phase 7) — routed, cached, circuit-broken

Nothing above `app/providers/` knows which upstream produced a row. The router is
itself a `ChainProvider`, so ingest and traversal call it exactly as they would
call a single API and never learn that failover happened.

```
ProviderRouter
 ├── EtherscanProvider     history + balance   (key)
 ├── BlockscoutProvider    history + balance   (keyless, opt-in)
 ├── AlchemyProvider       history + balance   (key)
 └── InfuraProvider        balance only        (key)

cache → in-process coalescing → cross-process single-flight
      → first capable provider whose circuit is closed → next on failure
```

**Providers declare capabilities.** Infura is a plain JSON-RPC node: it has no
address index, so there is no call that returns "every transaction touching this
address". Rather than stub that with an empty list — which downstream reads as
"this wallet has no activity", the most dangerous possible wrong answer — it
declares only `WALLET_INFO` and the router never asks it for history.

**Failures are classified, not merged.** A rate limit or 5xx is retried with
exponential backoff and full jitter, then fails over and counts toward opening
that provider's circuit. A malformed response fails over immediately, because an
identical request returns identical garbage. A capability gap is skipped silently
and never penalises the provider. Etherscan's habit of reporting throttling as
`HTTP 200` with the notice in the body is detected explicitly.

**Circuit breakers** stop a dead upstream from making every investigation slower
than having no provider at all: after N consecutive failures the circuit opens and
calls fail over without touching the network, then a single probe is allowed
through after a cooldown.

**Redis is on the request path now**, keyed by chain and address and never by
provider name — a page fetched from Blockscout satisfies a later request that
would have gone to Etherscan, so failover does not double upstream traffic. Ten
investigators opening the same wallet at the same moment produce one upstream
fetch: in-process via an async coalescer, and across processes via a best-effort
`SET NX PX` lock. If Redis is unreachable every one of these degrades to "just do
the work" — a cache outage must not become a platform outage.

Pull an address through the chain:

```bash
python -m app.ingest.chain_import --router --address 0x... --limit 500
```

Each imported row records the provider that actually served its page, so a store
fed by failover can still say where every transaction came from.

## Investigations (Phase 7) — the primary resource

A wallet lookup is a question; an **investigation** is the durable record of
having asked it. It is the resource the platform is organised around.

```
POST /investigations            {"chain": "ethereum", "address": "0x..."}
  -> 202  {"id": "INV-2026-00142", "status": "QUEUED"}

GET  /investigations/{id}              status + conclusion + methodology
GET  /investigations/{id}/graph
GET  /investigations/{id}/attribution
GET  /investigations/{id}/risk
GET  /investigations/{id}/evidence     flat records + integrity hash
GET  /investigations/{id}/report       PDF, rendered from the snapshot
```

`POST` never blocks on a traversal. It returns `202` immediately and the client
polls the id through `QUEUED → FETCHING → TRAVERSING → ANALYZING → COMPLETED`
(or `FAILED`, with the reason on the row). A pending investigation answers `409`
rather than `404` on its result routes — the resource exists, it just has no
result yet, and a poller must be able to tell those apart.

**Results are frozen.** On completion the graph, attribution, risk, evidence and
methodology are written once to an `investigation_snapshot`, and every result
route reads that snapshot instead of recomputing. If the chain reorgs, a label is
corrected, or the model is retrained tomorrow, yesterday's report still says what
it said the day it was filed. To change a conclusion you run a new investigation;
both stay on the record.

**Evidence is sealed.** Each snapshot carries a SHA-256 over the canonical
evidence records — keys sorted, timestamps normalised to UTC, floats at fixed
precision, records order-independent. Two runs over identical data produce the
same hash, and altering any observation changes it. The hash is printed in the
PDF's *Provenance & integrity* block.

**Identity is `(chain, address)`, never address alone.** The same 20-byte address
exists on every EVM chain and belongs to different parties there. Transactions,
labels, wallets and investigations are all chain-scoped, and a traversal never
crosses chains — funds that move between chains do so through a bridge, which is
a labeled endpoint on both sides.

The older `/wallets/{addr}/*` routes remain as ad-hoc lookups. They recompute on
every call and leave no record, which is exactly why they are not the primary
resource.

### In the UI

`/investigations` opens one and lists the rest; `/investigations/{id}` watches it
run and then shows the result:

- a **stage track** that names the phase being executed, because a real traversal
  is slow enough that a bare spinner tells an investigator nothing;
- **methodology & integrity** alongside the verdict — model version, data
  provider, traversal bounds, data timestamp, and the evidence hash — rather than
  buried in the PDF;
- an **evidence ledger**: the flat records exactly as they were hashed, one row
  per observed transaction with its own content-derived id, so a reviewer can
  cite a single line instead of "the deposit-sweep signal".

The list auto-refreshes while any investigation is still running and stops once
everything reaches a terminal state.

## Continuous integration

`.github/workflows/ci.yml` runs the same gates that run locally — `ruff`, `mypy
--strict`, `pytest`, plus `alembic upgrade` / `alembic check` / a full downgrade,
and the frontend's `tsc --noEmit` and `next build`. The migration check is there
because model-vs-migration drift is the failure that silently ships a column the
deployed database does not have.

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
