set shell := ["bash", "-lc"]

# Show available commands
default:
    @just --list

sanity:
    docker compose exec -e DATABASE_URL=sqlite+pysqlite:///:memory: api-dev python scripts/sanity_check.py

test:
    docker compose exec -e DATABASE_URL=sqlite+pysqlite:///:memory: api-dev pytest

lint:
    docker compose exec api-dev ruff check .

format:
    docker compose exec api-dev ruff check --select I --fix .
    docker compose exec api-dev ruff format .

make_migrations name="auto":
    docker compose exec api-dev alembic revision --autogenerate -m '{{name}}'

migrate:
    docker compose exec api-dev alembic upgrade head

dev-up:
    docker compose up -d db api-dev

dev-down:
    docker compose stop api-dev db

alembic *args:
    docker compose exec api-dev alembic {{args}}

lint-web:
    cd frontend && npx @biomejs/biome check --write
