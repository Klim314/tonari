# Phase 4 Review

## Review — Codex — 2026-04-17

**Files reviewed**: `backend/app/routers/works.py`, `backend/app/schemas.py`, `backend/app/models.py`, `backend/services/explanation_service.py`, `backend/services/explanation_workflow_v2.py`, `backend/agents/explanation_generator_v2.py`, `backend/agents/prompts.py`, `backend/alembic/versions/d4a1e7f3b2c9_add_work_jlpt_level.py`
**Changes**: Review of the current JLPT-level explanation calibration delta

### Critical
- **[backend/services/explanation_service.py:29]** The new JLPT level never participates in artifact identity. Artifact lookup/creation still keys only on `(segment_id, span_start, span_end, density)`, and the DB uniqueness constraint in `translation_explanations` still matches that same key. The POST/stream paths in `works.py` now pass `work.jlpt_level` into generation, but once an artifact already exists the workflow reuses or replays it regardless of learner level. Changing a work from `N5` to `N1` will therefore keep serving the old cached explanation until someone forces regeneration or manually clears the row. Suggested fix: persist the effective JLPT level on the artifact and include it in lookup/uniqueness, or invalidate existing explanation artifacts when `work.jlpt_level` changes.

### Important
- **[backend/app/routers/works.py:135]** `PATCH /works/{work_id}` cannot distinguish “field omitted” from “explicitly set to null”. `WorkUpdateRequest.jlpt_level` defaults to `None`, and the route’s `else` branch always clears `work.jlpt_level`. An empty `{}` patch body therefore silently resets the learner level, and the same bug will apply to any future partial-update call that does not include `jlpt_level`. Suggested fix: check `body.model_fields_set` (or equivalent) and only mutate `work.jlpt_level` when the field was actually provided.

### Summary
The learner-level direction is reasonable, but the current delta is not safe to merge yet because explanation caching is still level-agnostic. Existing workflow tests pass, but there are no JLPT-specific tests covering cache invalidation or the new work update route.

---
