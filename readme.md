# Tonari

Tonari is a translation workbench for scraped works and chapter-based literary translation. The
current app supports:

- importing works from supported source URLs
- scraping chapter ranges into the local database
- assigning prompts and prompt versions to works
- streaming chapter translation segment-by-segment
- regenerating segments, manually editing segment output, and generating explanations
- organizing chapters into groups from the work detail view

## Stack

- Frontend: React 19, TypeScript, Chakra UI v3, Vite
- Backend: FastAPI, SQLAlchemy, Alembic
- Local dev: Docker Compose + `just`

## Development

Run from the repo root:

```bash
just dev-up
```

Useful commands:

- `just dev-up` starts Postgres, `api-dev`, and `frontend`
- `just dev-down` stops the dev containers
- `just test` runs the backend test suite
- `just lint` / `just format` run Ruff in the backend container
- `just lint-web` / `just format-web` run Biome in `frontend/`
- `just migrate` runs Alembic migrations
- `just makemigrations name="..."` creates a new migration
- `just generate-api` refreshes the frontend API client from the running backend

The backend dev server runs on `http://localhost:8087`. The frontend dev server runs on
`http://localhost:5173`.

## Repo Layout

- `backend/` FastAPI app, models, services, routers, tests, and Alembic migrations
- `frontend/` React UI, generated API client, hooks, and page/components
- `docs/` focused project docs for current workflows

## Current Entry Points

- Backend app: `backend/app/main.py`
- Frontend app shell: `frontend/src/App.tsx`
- Task runner: `justfile`

## Docs

- `docs/translation-agent.md` translation configuration and runtime behavior
- `backend/README.md` backend-oriented development workflow
- `AGENTS.md` / `CLAUDE.md` agent-specific repo instructions
