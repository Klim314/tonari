# Backend

FastAPI backend for works, chapters, prompts, scraping, and translation streaming.

## Dev Workflow

Primary development commands live in the root [README](/mnt/d/projects/tonari/readme.md).

The backend runs inside the `api-dev` container. The dev API is available at
`http://localhost:8087` and reloads automatically when files under `backend/` change. The
frontend dev server runs at `http://localhost:5173` and proxies API requests to `api-dev`.

If container dependencies change, rebuild the relevant image with `docker compose build api-dev`
or `docker compose build api`.

## Direct Host Execution

Docker is the default path, but direct host execution is still possible:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8087
```

## Migrations

Alembic lives under `backend/alembic/`.

Use the root-level `just migrate` and `just makemigrations` commands for normal development.

Direct Alembic invocation is only needed when working inside the backend container or debugging
migration behavior manually:

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

From the repo root, `just migrate` and `just makemigrations` run those commands inside the dev
container.

## Current Backend Surface

Main app entry point: `backend/app/main.py`

Current router groups:

- `/health` basic health check
- `/works` work import, chapter listing, scrape orchestration, translation state and streaming,
  segment regeneration and editing, explanation streaming, chapter groups
- `/prompts` global prompts, prompt versions, and work-level prompt assignment
- `/models` supported translation model metadata
- `/lab` prompt-lab translation streaming endpoint
- `/ingest` legacy ingest endpoints still present in the app
- `/chapter-translations` lower-level translation records and segment listing

## Current Data Model

Core tables currently represented in `backend/app/models.py`:

- `works` and `chapters`
- `chapter_translations` and `translation_segments`
- `prompts`, `prompt_versions`, and `work_prompts`
- `scrape_jobs`
- `chapter_groups` and `chapter_group_members`

This is the live schema shape for the current app. Older planning docs that mention artifact
storage, workers, Redis, or export tables should not be treated as authoritative.

## Notes

- Configuration lives in `backend/app/config.py` and `.env`.
- Tests live under `backend/tests/`.
- Imports use the `app.*`, `services.*`, and `agents.*` package layout used throughout the repo.
