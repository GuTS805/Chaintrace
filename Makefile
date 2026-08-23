# VASP Attribution Platform — dev workflow
# Windows note: run these from Git Bash / WSL, or invoke the commands directly.

BACKEND := backend
PY := python

.PHONY: help install up down migrate revision test lint typecheck seed-demo ingest-labels dev

help:
	@echo "install       - install backend deps (editable, with dev extras)"
	@echo "up            - start postgres + redis (docker-compose)"
	@echo "down          - stop containers"
	@echo "migrate       - apply Alembic migrations to the DB"
	@echo "revision m=.. - autogenerate a new migration"
	@echo "test          - run pytest (offline, SQLite)"
	@echo "lint          - ruff check"
	@echo "typecheck     - mypy strict on app/"
	@echo "ingest-labels - load bundled offline label sources into the DB"
	@echo "seed-demo     - seed demo fixtures (Phase 2, offline)"
	@echo "dev           - run the API with autoreload"

install:
	cd $(BACKEND) && $(PY) -m pip install -e ".[dev]"

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	cd $(BACKEND) && alembic upgrade head

revision:
	cd $(BACKEND) && alembic revision --autogenerate -m "$(m)"

test:
	cd $(BACKEND) && $(PY) -m pytest -q

lint:
	cd $(BACKEND) && ruff check .

typecheck:
	cd $(BACKEND) && mypy

ingest-labels:
	cd $(BACKEND) && $(PY) -m app.ingest.labels

seed-demo:
	cd $(BACKEND) && $(PY) -m app.synthetic.seed

train:
	cd $(BACKEND) && $(PY) -m app.attribution.train

dev:
	cd $(BACKEND) && uvicorn app.main:app --reload
