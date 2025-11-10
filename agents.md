# Agent Setup Notes

- Prefer the `Justfile` helpers (e.g., `just test`, `just sanity`, `just alembic ...`) instead of invoking `docker compose` manually. They already wrap the compose commands, set `DATABASE_URL` for tests (`sqlite+pysqlite:///:memory:`), and target the correct containers.
- Backend commands (pytest, Alembic) should run inside the `api-dev` container; bring everything up with `docker compose up -d db api-dev` before running the Just recipes.
- Schema changes require Alembic migrations plus `just alembic upgrade head` to keep the dev Postgres schema aligned; revisions live in `backend/alembic/versions`.
- Python tooling is not installed on the host, so running tests or scripts locally will fail unless you add the dependencies—stick to the containerized environment unless you explicitly install them.
- Frontend linting runs through `just lint-web` (Biome). Use that target instead of calling `npm run lint` directly so it picks up the right toolchain.

## Dependency Notes

- The frontend uses **Chakra UI v3** (Chakra Next), not v2. Component imports and theming APIs should follow the v3 docs when adding UI features.
