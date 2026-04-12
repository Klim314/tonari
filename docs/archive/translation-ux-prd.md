# Translation UX PRD (Draft)

## Goals
- Improve post-translation iteration without forcing full retranslate cycles.
- Let users make targeted edits while preserving context and style.
- Avoid per-line requery loops for work translation batches.
- Keep the MVP constrained to segment-level changes only.

## Feature 1: Suggest Improvements
- User story: As a reader, I want suggestions to polish a translation so I can accept targeted edits without regenerating everything.
- Entry point: New action button in the post-translation actions: `Suggest Improvements`.
- Input: A text field for user instructions to guide the improvement pass.
- Output: A short list of proposed edits with rationale and a minimal diff.
- Controls: `Apply all`, `Apply selected`, `Discard`.
- Batch behavior: Run once per translation job (not per line). Suggestions can reference specific segments by index.
- MVP scope: Suggestions must be scoped to segment-level changes only (no full-document rewrites).
- Constraints: No quality grading; focus on actionable improvements (tone, clarity, consistency, literalness, terminology).
- Safeguards: If model confidence is low or suggestions would be too broad, return "no suggestions" and explain briefly.

## Feature 2: Manual Edit + Apply
- User story: As a reader, I want to directly edit the translation and keep changes.
- Entry point: New action button: `Edit Translation`.
- UI: Segment-level editor with original translation and source context side-by-side.
- Controls: `Save edits`, `Cancel`, `Apply to selected segments` (required for MVP).
- Post-save: Return the updated translation only. No diff in MVP.
- Constraints: No auto retranslate during editing; user edits are authoritative.

## Interaction Flow (High Level)
- Translate -> show translation -> actions: `Explain`, `Suggest Improvements`, `Edit Translation`, `Try Another Version`.
- Suggest Improvements -> user adds instructions -> returns list -> user applies -> updated translation -> optional `Explain`.
- Edit Translation -> save -> updated translation -> optional `Explain`.

## Out of Scope
- Versioned translation storage or diff history.
- Persisted `translation_version` metadata (source, model, timestamps, kind).
- Storing or showing diffs for suggestions and manual edits.

## Data & API Considerations (MVP)
- Use existing translation models; do not add new versioned-translation tables.
- Suggestions response format: array of `{segment_id, before, after, rationale, confidence}`.
- Manual edits payload: `{translation_id, edited_text_by_segment}`.
- Suggest improvements payload: `{translation_id, instructions}`.

## Non-Goals
- Auto-updating system prompts or global profile from edits.
- Per-line requery loops during batch translations.

## Metrics
- Suggestion acceptance rate.
- Manual edit usage rate.
- Retranslate rate reduction.
- Average time to "final" translation.

## Open Questions
- Source and translation are already segmented via `translationSegments`.
- Retranslate overwrites existing translations; manual edit overwrites and saves to server.
