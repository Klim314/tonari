# Work Prompt System To-Dos

## Context
- Each work may have a single `Prompt` record that stores the prompt name and links to version history.
- A `PromptVersion` contains the model, f-string template, optional metadata/parameters, author, and timestamps.
- Chapter translations always consume the latest prompt version for that work and must record which version + parameters were used at generation time.

## Data Model & Persistence
- [ ] Create Alembic migration adding `prompts` and `prompt_versions` tables with the described columns and FK/unique constraints (one prompt per work, monotonic version numbers per prompt).
- [ ] Extend `chapter_translations` with `prompt_version_id` (FK), `model_snapshot`, `template_snapshot`, and `parameters_snapshot` JSONB columns; backfill historical rows with `NULL` FK and default snapshots representing the legacy global prompt.
- [ ] Update SQLAlchemy models (`backend/app/models.py`) and Pydantic schemas (`backend/app/schemas.py`) to represent prompts, versions, and the new chapter translation fields.

## Backend APIs & Services
- [ ] Introduce a `WorkPromptService` (or similar) that encapsulates fetching/creating prompts, appending versions, and rendering templates with validation.
- [ ] Add router endpoints under `/works/{work_id}/prompt` for GET (prompt + versions), POST (create prompt), POST `/versions` (append version), and optional PATCH for renaming.
- [ ] Ensure translation pipeline (`translation_service.py` + `translation_stream.py`) loads the latest prompt version, renders the template with chapter/work context, and supplies the selected model + metadata to downstream agents.
- [ ] When saving a `chapter_translation`, persist the `prompt_version_id` and snapshot columns captured above.
- [ ] Validate prompt templates by dry-running `.format_map` (or equivalent) to fail fast on missing variables; expose useful error messages via API responses.

## Frontend UX
- [ ] Extend `ChapterDetailPage.tsx` (or dedicated Work page section) with a “Work Prompt” panel showing current model, template, metadata, version number, timestamp, and author.
- [ ] Implement an “Edit Prompt” modal that lets operators adjust the name, select a model, edit template text, and provide optional metadata; submitting should create a new prompt version via the backend endpoint.
- [ ] Display version history (accordion/table) with ability to expand entries, view diffs, and trigger “revert” by cloning an older version into a new one.
- [ ] Show chapter translation cards/badges referencing the prompt version and model used (coming from snapshot data) so users can audit runs.

## Testing & Ops
- [ ] Write unit/integration tests for the new service layer and router endpoints (pytest inside `api-dev`).
- [ ] Add regression tests ensuring translation generation records prompt snapshots and respects per-work models.
- [ ] Update docs (e.g., `docs/translation-agent.md`) to describe prompt variables, allowed models, and workflow for editing prompts.
- [ ] Provide a `just` helper or admin script to seed default prompts for all existing works, if needed.

