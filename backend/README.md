# Backend (FastAPI) — Dev with uv

## Prereqs
- Python 3.11+
- uv (https://github.com/astral-sh/uv)
- Docker (optional, for Postgres)

## Start Postgres (non-default port)

Use Docker to avoid clashes with local services:

```
docker compose up -d db
```

Connection string (place in `backend/.env`):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:55432/tonari
```

## Install deps and run API

From `backend/`:

```
uv sync
uv run uvicorn app.main:app --reload --port 8087
```

API will be at http://localhost:8087

## Basic flow
- Ingest a Syosetu chapter: `POST /ingest/syosetu { "url": "https://ncode.syosetu.com/..." }`
- Create a chapter translation: `POST /chapter-translations { "chapter_id": <id> }`
- Fetch segments: `GET /chapter-translations/{id}/segments`

Note
- This prototype uses a fixed stub translator and naive sentence splitter. Replace with LLM later.
- Imports are absolute (`app.*`) per project convention.
