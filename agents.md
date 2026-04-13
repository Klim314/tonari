# Tonari

## Project Structure

The project uses:
- **Frontend:** React with TypeScript, Chakra UI v3
- **Backend:** Python FastAPI with Alembic migrations
- **Docker:** Docker Compose for local development
- **Package Manager:** npm (frontend), pip (backend)

## Development Commands

This project uses `just` as a task runner. See `justfile` for all available commands:

**Common commands:**
- `just dev-up` - Start development environment (db, api-dev, and frontend)
- `just dev-down` - Stop development environment
- `just test` - Run backend tests
- `just lint` - Lint backend code
- `just format` - Format backend code
- `just lint-web` - Lint frontend code with Biome
- `just format-web` - Format frontend code with Biome
- `just migrate` - Run database migrations
- `just makemigrations [name]` - Generate new migration
- `just generate-api` - Generate frontend API client from OpenAPI spec
- `just --list` - See all available just recipes

## Long-Running Task Tracking

Multi-session tasks live under `.ai/active/`. Each subdirectory is a self-contained task.

Progress uses a two-file pattern:

- **`state.md`** — Compact current state: status, summary table, next steps, blockers. Overwritten each session. Read this first when resuming.
- **`log.md`** — Append-only session history. Only consult when you need to understand past decisions.

When starting a session: read `state.md`. When ending: overwrite `state.md`, append to `log.md`.

## Agents-Specific Instructions (Gemini / Codex)

### Long-Running Task Tracking

When working on multi-session tasks under `.ai/active/`, use a two-file pattern for progress tracking:

- **`state.md`** — Compact current state. Contains: status, findings/task summary table, current focus, next steps, blockers, open questions. **Overwritten** (not appended to) each session to stay small. This is what you read first when resuming work.
- **`log.md`** — Append-only session history. Add a dated entry at the end of each session summarizing what was done and decisions made. Only read this when you need to understand *why* a past decision was made.

The goal: `state.md` stays small enough to always fit in context. `log.md` grows freely but is never loaded by default.

When starting a session on an existing task:
1. Read `state.md` to understand current state
2. Do the work
3. Overwrite `state.md` with updated state
4. Append a session entry to `log.md`

### Active Tasks

See `.ai/active/` for in-progress work. Each subdirectory is a self-contained task with its own process docs and artifacts.
