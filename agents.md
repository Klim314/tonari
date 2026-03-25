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

## Agents-Specific Instructions (Gemini / Codex)

<!-- Add instructions specific to Gemini and Codex here -->
