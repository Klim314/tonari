# North Star: Automated Literary Translation Platform

## Vision
- Automation-first literary translation with strong provenance, cost control, and reproducibility.
- Bulk side-by-side outputs (aligned segments) suitable for readers and editors.
- JP→EN focus initially; enable reuse over recompute with prompt+model versioning.

## Problem
- Ad hoc copy/paste is wasteful and irreproducible.
- MT historically misses literary style, tone, and phonetics; LLMs need structure.
- Repeated re-translation under changing prompts wastes compute and loses provenance.

## Target Users
- Bilingual hobbyists and fan translators (JP→EN) and readers of bilingual outputs.
- Prompt tinkerers iterating for style/tone; editors consolidating best fragments later.

## Core Principles
- Automation-first: no per-line approvals in MVP; jobs run end-to-end.
- Provenance-by-default: every output ties to source, prompt version, model, params.
- Reuse over recompute: deterministic segment-level caching via content hashing.
- Aligned outputs: 1:1 mapping of source segments to translations.
- Non-blocking QA: flags inform review; never block completion in MVP.

## End-to-End Flow
1. Ingest: identify work → fetch/normalize chapters (store `normalized_text`, `text_hash`).
2. Configure: select prompt version + model config; choose cache policy (reuse | no-reuse).
3. Translate (LLM-guided spans): for each chapter, the LLM returns an ordered list of spans `{start, end, tgt, flags}` referencing the chapter text; validate offsets and store as translation segments.
4. QA: compute non-blocking flags (length, lang-id, untranslated %, glossary coverage) per segment and summary per chapter.
5. Export: build bilingual JSONL (bitext), bilingual Markdown, and target-only Markdown artifacts for the chapter translation.

## Architecture (MVP)
- API: lightweight service (FastAPI or Node/Express) for CRUD + job orchestration.
- Worker: queue (Redis-backed) executes translation, QA, exports.
- DB: Postgres for metadata and artifacts (JSONB). No object storage in MVP.
- Cache: Redis for hot results; persistent cache via `translations.hash` in Postgres.
- Frontend: React + Chakra UI (Vite, React Router, TanStack Query) for jobs, prompts, viewer.

## Frontend (React + Chakra)
- Pages: Dashboard, Works/Chapters, Prompts (with version diffs), Jobs, Bilingual Viewer.
- Components: PromptEditor, JobCreator, JobTable, SegmentTable, BilingualViewer, FlagsBadge, CostSummary.
- Theme: readable line-by-line layout; light/dark via Chakra theme tokens.

## Data Model (High-Level)
- works(id, title, source_meta jsonb, created_at)
- chapters(id, work_id, idx, title, normalized_text text, text_hash text, created_at)
- prompts(id, name, created_at)
- prompt_versions(id, prompt_id, body text, meta jsonb, created_at)
- model_configs(id, provider, name, params jsonb, created_at)
- chapter_translations(id, chapter_id, prompt_version_id, model_config_id, status, cache_policy, params jsonb, cost_cents, meta jsonb, created_at)
- translation_segments(id, chapter_translation_id, start int, end int, order_index int, tgt text, flags jsonb, cache_key text, src_hash text, created_at)
- artifacts(id, chapter_translation_id, kind text, format text, data jsonb, size_bytes int, created_at)

Indexes: translation_segments(chapter_translation_id), translation_segments(cache_key), chapters(work_id, idx).

## Artifact Formats (Stored in Postgres JSONB)
- bitext (jsonl): `data.lines[] = { src_id, src, tgt, flags[] }` where `src` is sliced from `chapters.normalized_text[start:end]`
- bilingual_md (md): `data.content = string`
- target_md (md): `data.content = string`
- qa_summary (json): `data = { counts, ratios, samples[] }`

## Default Prompt Spec (Automation-First)
- System: “You are a literary translator. Output JSON only. No commentary.”
- Instructions (LLM-guided spans):
  - Given the chapter text/window, split into coherent translation units and output an array of objects with fields: `start` (int), `end` (int), `tgt` (string), `flags` (array of strings).
  - Offsets are 0-based indices into the provided text, non-overlapping and ordered; do not cross window boundaries.
  - Do not include or modify source text in output; fidelity over style on conflicts; add a flag when constraints collide.
- Inputs: `original_text`, optional `glossary[]`, `style_notes`.
- Determinism: optional. Allow retries; control reuse via `cache_policy`.

Example output:
{"segments":[
  {"start":0,"end":6,"tgt":"\"Are you going?\"","flags":[]},
  {"start":6,"end":15,"tgt":"He shook his head.","flags":["tone_softened"]}
]}

## Japanese Focus (JP specifics)
- Segmentation: punctuation-light handling; MeCab/Kuromoji-like heuristics.
- Readings: optional furigana/reading notes; kana/romaji toggles (viewer-only).
- Honorifics: policy options (retain/translate/annotate); glossary enforcement.
- Name consistency: entity memory + glossary support.

## Quality & Evaluation (Non-Blocking)
- Auto metrics: length ratio, lang-id, untranslated tokens %, glossary coverage.
- Human review: optional post hoc; not required for MVP.
- Output enforcement: strict JSON schema validation + repair pass for offsets; fallback to rule-based segmentation on repeated failures.
- Regression protection: pin baselines; detect major drifts in later versions.

## Non-Functional & Ops
- Cost control: per-job budget caps, token usage estimates, and logs.
- Observability: segment/job logs, retries, failure categories, QA summaries.
- Backups: Postgres dumps capture metadata and artifacts.
- Legal/ToS: start with public-domain sources (e.g., Aozora) + user uploads.

## MVP Scope (4–6 Weeks)
- Ingest: Aozora/public-domain + file uploads (TXT/MD). Deterministic segmenter.
- Prompt versioning (basic) + single model integration.
- Bulk translation with segment cache; artifacts in Postgres JSONB.
- Bilingual viewer (flags filter), exports (JSONL bitext, bilingual MD, target-only MD).
- Dashboard: jobs, status, basic costs, QA summaries. Minimal auth.

## V1 Enhancements
- Glossary/style enforcement; prompt diffs; job compare across prompt versions.
- EPUB/TMX exports; batch reruns by chapter/flag; multi-model compares.
- Optional light HITL overlay focused on flagged segments only.
