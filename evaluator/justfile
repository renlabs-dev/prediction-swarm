# Database Management Commands

# Start PostgreSQL database
db-start:
    docker-compose up -d

# Stop database and remove volumes (WARNING: deletes all data)
db-stop:
    docker-compose down -v
    docker volume prune -f

# Alembic Migration Commands

# Create a new migration
migrate-create MESSAGE:
    cd src/db && uv run alembic revision --autogenerate -m "{{MESSAGE}}"

# Apply all pending migrations
migrate-up:
    cd src/db && uv run alembic upgrade head

# Rollback one migration
migrate-down:
    cd src/db && uv run alembic downgrade -1

# Show migration history
migrate-history:
    cd src/db && uv run alembic history

# Show current migration
migrate-current:
    cd src/db && uv run alembic current

# Show pending migrations
migrate-pending:
    cd src/db && uv run alembic heads

# Application Commands

# Run the prediction extractor
run:
    uv run python src/prediction_extract.py

# Run the evaluation CLI
evaluate:
    uv run python -m src.evaluator

# Run evaluation from a specific date (YYYY-MM-DD)
evaluate-from DATE:
    uv run python src/evaluator.py from {{DATE}}

# Show evaluation statistics
evaluate-stats:
    uv run python src/evaluator.py stats

# Run type checking
typecheck:
    uv run mypy src/

# Run linting
lint:
    uv run ruff check .

# Run formatting
format:
    uv run ruff format .

# Development Setup

# Initial setup: start db and create initial migration
setup: db-start
    sleep 5
    just migrate-create "Initial migration: add program iterations and evaluation tables"
    just migrate-up

# Reset everything: clean database, start fresh, and setup
reset: db-stop db-start
    sleep 5
    just migrate-create "Initial migration: add program iterations and evaluation tables"
    just migrate-up
