# Gemini Code Configuration for Tonari

This file documents the Gemini/Antigravity setup and available context for this project.

## Agent Guidelines & Operational Notes

### Execution Environment
- **Task Runner**: This project uses `just` as the primary task runner. Prefer `just` commands over raw `docker` or `npm` commands.
- **Containerization**: 
    - The backend environment (including Python tooling, pytest, Alembic) lives inside the `api-dev` container.
    - **Do NOT** try to run python/pip commands on the host directly.
    - **Do NOT** run `npm` commands directly for startup. Use Docker.
    - **Startup**: 
        - Backend only: `just dev-up`
        - Full Stack: `docker compose up -d` (starts db, api-dev, and frontend)
- **Database**: Tests use `sqlite+pysqlite:///:memory:` but dev environment uses Postgres. `just alembic upgrade head` keeps local schema in sync.

### Frontend Standards
- **Framework**: React with TypeScript.
- **UI Library**: **Chakra UI v3** (Chakra Next). 
    - **Important**: Do not use v2 patterns. Refer to v3 documentation/patterns.
- **Icons**: Use `lucide-react`. Avoid Chakra's built-in icons unless requested.
- **Linting**: Use `just lint-web` (Biome). Do not use `npm run lint`.

## Project Structure

- **Frontend**: `frontend/` (React, Vite/Next, Chakra v3, Biome)
- **Backend**: `backend/` (FastAPI, Alembic, Pydantic)
- **Infrastructure**: `docker-compose.yml`, `Justfile`

## Command Reference

Use `just --list` to see all recipes. Common commands include:

| Command | Description |
| :--- | :--- |
| `docker compose up -d` | Start full stack (db, api-dev, frontend) |
| `just dev-up` | Start development environment (db and api-dev) |
| `just dev-down` | Stop development environment |
| `just test` | Run backend tests (runs in `api-dev`) |
| `just lint` | Lint backend code |
| `just format` | Format backend code |
| `just lint-web` | Lint frontend code (Biome) |
| `just migrate` | Run database migrations |
| `just makemigrations [name]` | Generate new migration (e.g. `just makemigrations add_user`) |
| `just generate-api` | Generate frontend API client from OpenAPI spec |

## Browser
localhost:5173