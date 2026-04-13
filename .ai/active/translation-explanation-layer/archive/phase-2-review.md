# Code Review — Explanation System v2

> **Status:** Temporary review artifact. Delete after all issues are resolved.
> **Reviewer:** Claude (Review-Agent / Opus) — agent `a4112099b11c75a95`
> **Date:** 2026-04-12
> **Branch:** main
> **Scope:** New explanation v2 files + modifications to `works.py`

## Files Reviewed

- `backend/agents/explanation_generator_v2.py` *(new)*
- `backend/app/explanation_schemas.py` *(new)*
- `backend/services/explanation_service.py` *(new)*
- `backend/services/explanation_workflow_v2.py` *(new)*
- `backend/app/routers/works.py` *(modified — new SSE/REST endpoints)*
- `backend/tests/test_sentence_splitter.py` *(new)*

---

## Fix Priority Order

| Priority | Issue | Severity | Effort |
|---|---|---|---|
| 1 | ~~C-1 — TOCTOU race in `get_or_create`~~ | Critical | Medium |
| 2 | ~~I-1a — Partial facets finalized as `complete` (cache corruption)~~ | Important → **should be Critical** | Medium |
| 3 | ~~I-1b — Span inputs never validated~~ | Important | Small |
| 4 | ~~I-1 — `mark_error` data loss~~ | Important | Small |
| 5 | I-2 — No null guard on `segment` | Minor | Trivial |
| 6 | ~~I-3 — Inline import~~ | Important | Trivial |
| 7 | ~~I-4 — `_get_preceding_context` type fragility~~ | Important | Small |
| 8 | I-5 — Sync DB blocks event loop | Important | Large (deferred) |
| 9–11 | ~~M-1 / M-2 / M-3 — Style/hygiene~~ | Minor | Trivial |

> **Reviewer note:** I-1a is under-classified as Important. The live SSE stream and cached replay diverge silently — a user who retries a failed explanation gets a permanently incomplete result with no signal that anything failed. This is a cache correctness bug with direct user-visible consequences, equivalent in severity to C-1.

---

## Critical

### C-1 — TOCTOU race in `ExplanationService.get_or_create`
**File:** `backend/services/explanation_service.py:50-93`

The SELECT and INSERT are not protected by any lock or unique-constraint-aware upsert. Two concurrent requests for the same `(segment_id, span_start, span_end, density)` will both see `existing is None`, both attempt INSERT, and one will raise an `IntegrityError` on `uq_explanation_segment_span_density` — surfacing as a 500 to the client.

**Fix:** Catch `IntegrityError` and re-query on conflict, or use `insert().on_conflict_do_nothing()` + re-SELECT:
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(Explanation).values(...).on_conflict_do_nothing()
session.execute(stmt)
session.flush()
return session.scalars(select(Explanation).where(...)).one()
```

**Status:** [x] Fixed — `SELECT … FOR UPDATE` on the segment row serializes concurrent `get_or_create` calls; lock held until `session.commit()`.

---

## Important

### I-1 — `mark_error` stores error message in a non-schema key (data loss)
**File:** `backend/services/explanation_service.py:135-139`

`raw["_error"] = message` stores the error outside `ArtifactPayload`. Pydantic v2 silently drops extra fields on validation, so the error message is lost on any subsequent read of the artifact.

**Fix:** Add an `error: str | None = None` field to `ArtifactPayload`, or use a dedicated `error_message` column on the model.

**Status:** [x] Fixed — added `error: str | None = None` to `ArtifactPayload`; `mark_error` now sets `payload.error = message` instead of using a `_error` raw dict key.

---

### I-1a ⚠️ — Partial facet failures are finalized as `complete` and disappear on replay *(recommend promoting to Critical)*
**File:** `backend/services/explanation_workflow_v2.py:161-227` / `backend/services/explanation_service.py:95-127`

Per-facet failures are persisted as `FacetEntry(status="error")`, but the workflow still calls `mark_complete()` unconditionally after the generation loop. Later cache replays only emit entries whose facet status is `"complete"`, so any failed facet is silently dropped while the artifact itself reports overall `status="complete"`.

This produces an inconsistent client contract:
- the live SSE stream can emit `explanation-error` for a facet,
- the stored artifact still looks successful at the top level,
- and subsequent GET / replay calls no longer expose the failed facet at all.

**Fix:** Track whether any facet failed during generation. If so, either:
- persist the artifact as overall `error` / `partial_error`, or
- replay errored facets explicitly and expose them through the GET response.

At minimum, `mark_complete()` should not run after any facet-level failure.

**Status:** [x] Fixed — `any_facet_error` flag tracked in the generation loop; calls `mark_error` instead of `mark_complete` on partial failure. Cache hit check extended to `status in ("complete", "error")`; `_replay_from_cache` now replays error facets as `ArtifactErrorEvent` and reflects actual status in the final `ArtifactCompleteEvent`.

---

### I-1b — Sentence span inputs are never validated against the actual segment/sentence boundaries
**File:** `backend/app/explanation_schemas.py:150-156` / `backend/app/routers/works.py:906-978` / `backend/agents/explanation_generator_v2.py:145`

The new sentence endpoints accept any `span_start >= 0` and any `span_end > 0`, but do not verify:
- `span_start < span_end`
- `span_end <= len(segment_source)`
- that the span matches one of the sentence spans already returned by the translation state API

The generator then slices `segment_source[span_start:span_end]` directly. That allows empty slices, out-of-bounds ranges, and arbitrary mid-sentence substrings to create cached explanation artifacts and potentially send an empty `<sentence>` block to the model.

**Fix:** Validate spans in preflight / start / stream against the segment source text and, if sentence-only explanations are intended, against the splitter-derived sentence spans for that segment. Reject invalid spans with `400`.

**Status:** [x] Fixed — `SpanValidationError` added to `services/exceptions.py`; `validate_span()` on `ExplanationWorkflowV2` checks `span_start < span_end` and `span_end <= len(segment_source)`. Called in `start()` and by the stream endpoint before `EventSourceResponse`; both catch and return 400.

---

### I-2 — No null guard on `segment` in `ExplanationWorkflowV2.stream`
**File:** `backend/services/explanation_workflow_v2.py:150-153`

`_get_segment` returns `TranslationSegment | None`, but `stream` accesses `segment.start`, `.end`, `.tgt`, `.order_index` immediately without a null check. On the current HTTP path this is not a normal bad-input case because the router performs preflight before opening the SSE stream. The realistic failure mode is a narrow TOCTOU race where the segment exists during preflight, then is deleted or regenerated before `stream` dereferences it. Today that most likely requires overlap with translation reset or segment regeneration, so the practical risk appears low, but the failure would still surface as an internal exception instead of a clean domain error.

**Fix:**
```python
segment = self._get_segment(...)
if segment is None:
    raise SegmentNotFoundError(f"segment {segment_id} not found")
```

**Status:** [ ] Skipped — low concurrency makes this race unlikely in practice. Deferred.

---

### I-3 — Inline import inside endpoint body
**File:** `backend/app/routers/works.py:917`

`from services.explanation_service import ExplanationService` is declared inside the function body. All other imports in this file are top-level.

**Fix:** Move to top-level imports alongside other service imports.

**Status:** [x] Fixed — moved to top-level, sorted with other `services.*` imports.

---

### I-4 — `_get_preceding_context` returns `list[dict]` where `list[SegmentContextInput]` is expected
**File:** `backend/services/explanation_workflow_v2.py:242-253`

Works today because `SegmentContextInput` accepts `Mapping[str, Any]`, but if `_render_block` ever validates keys strictly this will silently break. Implicit contract is fragile.

**Fix:** Return `SegmentContext` objects directly:
```python
return [SegmentContext(src=s.src, tgt=s.tgt) for s in preceding]
```

**Status:** [x] Fixed — both `_get_preceding_context` and `_get_following_context` now append `SegmentContext` objects; `SegmentContext` imported from `agents.base_agent`.

---

### I-5 — Synchronous DB session blocks event loop in async SSE path
**File:** `backend/services/explanation_service.py:7` / `backend/services/explanation_workflow_v2.py`

`ExplanationWorkflowV2.stream` is `async def` but calls synchronous `update_facet()` and `mark_complete()` directly, blocking the event loop on each facet persist during SSE streaming. This degrades throughput under concurrent SSE connections.

**Note:** Consistent with existing patterns in the codebase, so may be an accepted trade-off. Worth revisiting as concurrent usage grows.

**Fix (if prioritised):** Wrap sync DB calls in `asyncio.to_thread()` or migrate to an async SQLAlchemy session.

**Status:** [ ] Acknowledged / deferred

---

## Minor

### M-1 — Accessing private `BaseAgent` methods from outside the class
**File:** `backend/agents/explanation_generator_v2.py:107`

`BaseAgent._create_llm` and `_render_block` are accessed from outside the class, coupling the generator to `BaseAgent` internals.

**Status:** [x] Resolved — extracted as module-level `create_llm` and `render_block` in `base_agent.py`; `ExplanationGeneratorV2` imports and calls them directly.

---

### M-2 — `lru_cache` on module-level factory; `functools.cache` is clearer intent
**File:** `backend/agents/explanation_generator_v2.py:6`

`functools.cache` is an alias for `lru_cache(maxsize=None)` and makes the intent clearer. The miss path also isn't thread-safe for concurrent first calls (benign since the generator is stateless after init, but misleading).

**Status:** [x] Resolved — replaced `@lru_cache(maxsize=1)` with `@cache`.

---

### M-3 — `FACET_SCHEMA_MAP` has loose typing
**File:** `backend/app/explanation_schemas.py:92`

Typed as `dict[str, type]`; tighter as `dict[FacetType, type[AnyFacetData]]`.

**Status:** [x] Resolved — annotation updated to `dict[FacetType, type[AnyFacetData]]`.

---

## Summary

| Severity  | Count | Resolved | Skipped |
|-----------|-------|----------|---------|
| Critical  | 1     | 1        | 0       |
| Important | 6     | 5        | 1       |
| Minor     | 3     | 3        | 0       |

**Resolved:** C-1, I-1, I-1a, I-1b, I-3, I-4

**Skipped:** I-2 (low concurrency, deferred)

**Remaining:** I-5 (sync DB blocks event loop — acknowledged/deferred), M-1, M-2, M-3

Architecture and patterns are otherwise consistent with the rest of the codebase.
