# MVP Backlog

A pragmatic, implementation-ready list for a 4–6 week MVP. Automation-first, artifacts in Postgres JSONB, React + Chakra frontend.

## Database
- Create schema migrations for core tables: `works, chapters, prompts, prompt_versions, model_configs, chapter_translations, translation_segments, artifacts`.
- Add indexes: `translation_segments(chapter_translation_id)`, `translation_segments(cache_key)`, `chapters(work_id, idx)`.
- Implement `artifacts` JSONB with size tracking and basic constraints.
- Seed scripts: demo work with a few chapters and a sample chapter_translation.

## API (CRUD + Chapter Translations)
- CRUD: works (list/create/read), chapters (list/read), prompts/prompt_versions, model_configs.
- Chapter translations: `POST /chapters/{chapter_id}/translations` (create), `GET /chapters/{chapter_id}/translations` (list), `GET /chapter-translations/{id}` (status, costs), `GET /chapter-translations/{id}/segments` (span outputs).
- Artifacts: `GET /chapter-translations/{id}/artifacts` (list), `GET /chapter-translations/{id}/artifacts/{kind}`.
- Hashing/reuse: util to compute `cache_key = sha256(src_slice || prompt_version_id || provider || model || canonical_params)`.
- Cost tracking: record token usage and estimated cost per chapter translation.
- Error model: structured errors for scraper/translation failures.

## Worker
- Queue: enqueue per-chapter translation, slide chapter into windows, fan out per returned span with concurrency and rate-limits.
- Segmentation+translation: LLM returns `{start,end,tgt,flags}`; validate offsets; sort and assign `order_index`.
- Cache: before translating each span, compute `cache_key`; if found and `cache_policy=reuse`, copy prior tgt/flags; else call provider.
- Auto QA: compute flags (length ratio, lang-id, untranslated %, glossary coverage).
- Artifact builders: bitext JSONL (lines array), bilingual MD, target-only MD, QA summary.
- Observability: per-span logs, retries, chapter summary.

## Connectors / Ingest
- Aozora/public-domain fetcher: chapter listing + content fetch; respect robots.
- File uploads: TXT/MD upload + chapter splitting; simple rules.
- Normalizer: newline normalization; store `normalized_text` + `text_hash`.

## Prompting
- Prompt templates with variables: `{style_notes, glossary[], register}`.
- Default automation prompt (LLM-guided spans): output JSON only with `{start,end,tgt,flags}`; no commentary.
- Prompt versioning: name, body, notes, labels.

## Frontend (React + Chakra)
- Scaffolding: Vite, React Router, Chakra, TanStack Query, ESLint/Prettier.
- Pages:
  - Dashboard: chapter translations table, status, cost summary, QA counts.
  - Works: list/add; Chapters: read-only source preview and translation list.
  - Prompts: list, create, view versions, diff body between versions.
  - Chapter Translation: create (select prompt version, model), view status, segments, artifacts.
  - Viewer: bilingual side-by-side, filter by flags, copy/export.
- Components: PromptEditor, ChapterTranslationCreator, ChapterTranslationTable, BilingualViewer, FlagsBadge, CostSummary.
- Theme: base tokens and typography tuned for readability.

## Testing & DevEx
- Unit tests: hashing util, QA metrics, artifact builders.
- Integration tests: job flow from enqueue to artifacts for a tiny chapter.
- Seed demo: script to run a mock translation provider (echo with tweaks) for local dev.
- Scripts: `dev api`, `dev worker`, `dev web`.

## Ops
- Configuration: `.env` for DB, Redis, provider keys; sane defaults.
- Backups: local `pg_dump` instructions and restore script.
- Rate limiting: per-provider; config in DB meta.
- Logging: structured logs with job_id/segment_id correlation.

## Acceptance Criteria (MVP)
- User can ingest a public-domain chapter, run a chapter translation, and view a bilingual side-by-side with flags.
- Re-running with unchanged prompt/model and `cache_policy=reuse` uses cache for matching spans.
- Exports are available as artifacts: JSONL bitext, bilingual MD, target-only MD.
- Postgres contains artifacts in JSONB; a single DB dump can restore all state.
- Frontend shows chapter translation status, costs, and QA summaries without blocking on flags.
