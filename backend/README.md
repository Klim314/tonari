# Backend (FastAPI) — Dev Workflow

## Tooling
- Docker + Docker Compose (containers persist between commands; no `--rm`)
- [just](https://github.com/casey/just) (command runner)
- Optional: Python 3.11 + [uv](https://github.com/astral-sh/uv) for direct host execution

## Everyday Commands (from repo root)

| Command | Description |
| --- | --- |
| `just dev-up` | Start Postgres + `api-dev` (FastAPI + `--reload`, mounted source) |
| `just dev-down` | Stop the dev containers without deleting them |
| `just sanity` | Smoke test via TestClient (runs inside `api-dev`, uses in-memory SQLite) |
| `just test` | Pytest suite (inside `api-dev`, SQLite override per run) |
| `just lint` / `just format` | Ruff check/format inside the running container |

Run `just dev-up` once per session; the containers stay alive, so repeated `sanity`, `test`, or `lint` commands are fast `docker compose exec` calls. When dependencies change, rebuild with `docker compose build api-dev` or `docker compose build api`.

The live dev API is available at http://localhost:8087 and reloads automatically whenever files under `backend/` change (mounted into the container). The dev image installs the backend in editable mode, so the running interpreter always references the bind-mounted source instead of the copy baked into the image.

If you prefer direct `uv` usage instead of Docker, you can still run:

```
uv sync
uv run uvicorn app.main:app --reload --port 8087
```

## Database Migrations (Alembic)

We now manage schema changes with Alembic. Common commands (from `backend/`):

| Command | Description |
| --- | --- |
| `alembic revision --autogenerate -m "msg"` | Create a new migration from model diffs |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Roll back the last migration |

For existing databases that pre-date Alembic, stamp the current schema once before upgrading:

```
cd backend
alembic stamp 0001_initial_schema
alembic upgrade head
```

New environments can simply run `alembic upgrade head` (tables will be created via migrations).

## Basic API Flow
- Ingest a Syosetu chapter: `POST /ingest/syosetu { "novel_id": "n4811fg", "chapter": 2 }`
- Create a chapter translation: `POST /chapter-translations { "chapter_id": <id> }`
- Fetch segments: `GET /chapter-translations/{id}/segments`

Note
- This prototype uses a fixed stub translator and naive sentence splitter. Replace with LLM later.
- Imports are absolute (`app.*`) per project convention.
