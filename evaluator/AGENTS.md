# Repository Guidelines

## Project Structure & Module Organization
- src/: Python package with core modules (`evaluator.py`, `api_client.py`, `prediction_extract.py`, `schemas.py`, `config.py`).
- src/db/: Database layer (`models.py`, `database.py`, `db_service.py`) and Alembic migrations under `alembic/versions/` plus `alembic.ini`.
- justfile: Developer tasks (DB, migrations, run, lint, typecheck, format).
- docker-compose.yml: Local PostgreSQL (db: `swarm_evaluator`, user/pass: `postgres`).
- pyproject.toml: Python 3.12, dependencies, and tooling config (ruff, mypy).
- env/.env: Optional environment file loaded by `src/config.py`.

## Build, Test, and Development Commands
- DB up: `just db-start` (starts PostgreSQL via Docker).
- Migrations: `just migrate-create "<message>"`, `just migrate-up`, `just migrate-down`.
- Run extractor: `just run` (executes `src/prediction_extract.py`).
- Run evaluator CLI: `just evaluate` or `just evaluate-from 2025-09-01`; stats: `just evaluate-stats`.
- Lint/format/typecheck: `just lint`, `just format`, `just typecheck`.
- Without just: prefix with `uv run`, e.g. `uv run python -m src.evaluator`.
- Setup/reset: `just setup` (init DB + first migration), `just reset` (DESTROYS volumes; use with care).

## Coding Style & Naming Conventions
- Formatting: ruff with 80 char line-length, double quotes, spaces; run `just format`.
- Linting: ruff checks; run `just lint` and fix warnings.
- Types: mypy strict; add annotations and satisfy `just typecheck`.
- Naming: modules/files snake_case; classes CamelCase; functions/vars snake_case; constants UPPER_SNAKE.

## Testing Guidelines
- Current state: no test suite committed. Prefer pytest.
- Layout: create `tests/` mirroring `src/` (e.g., `tests/test_evaluator.py`).
- Naming: `test_*.py` and `Test*` classes; keep tests deterministic.
- DB: use Docker Postgres for integration tests or mock DB service for unit tests. Apply migrations before running.
- Run: `uv run pytest` (add to justfile if needed).

## Commit & Pull Request Guidelines
- History shows short imperative messages; no strict convention. Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- PRs: clear description, linked issues, reproduction/verification steps (e.g., commands run), and note schema changes. Include Alembic migration files in `src/db/alembic/versions/`.
- CI hygiene: ensure `just lint`, `just format`, and `just typecheck` pass before opening/merging.

## Security & Configuration Tips
- Secrets: do not commit credentials. Place API keys in `env/.env` or environment; `OPENROUTER_URL` is read by config.
- DB defaults are local-only; change for non-local use. Be careful with `just reset` — it prunes volumes and data.
