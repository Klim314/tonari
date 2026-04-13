set shell := ["bash", "-lc"]

# Show available commands
default:
    @just --list

test *args:
    docker compose exec -e DATABASE_URL=sqlite+pysqlite:///:memory: api-dev pytest {{args}}

lint:
    docker compose exec api-dev ruff check .

lint-fix:
    docker compose exec api-dev ruff check --fix .

format:
    docker compose exec api-dev ruff check --select I --fix .
    docker compose exec api-dev ruff format .

makemigrations name="auto":
    docker compose exec api-dev alembic revision --autogenerate -m '{{name}}'

migrate:
    docker compose exec api-dev alembic upgrade head

dev-up:
    docker compose up -d db api-dev frontend

dev-down:
    docker compose stop frontend api-dev db

lint-web:
    docker compose run --rm --no-deps frontend npm run lint

format-web:
    docker compose run --rm --no-deps frontend npm run format

typecheck:
    docker compose run --rm --no-deps frontend npm run typecheck

generate-api:
    curl -fsSLo frontend/openapi.json http://localhost:8087/openapi.json && npm --prefix frontend run generate:api

# Sync .ai/ instructions to platform files (CLAUDE.md, AGENTS.md)
ai-sync:
    bash .ai/sync.sh
