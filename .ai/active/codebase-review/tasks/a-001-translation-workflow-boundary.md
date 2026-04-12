# A-001 Task Plan — Translation Workflow Boundary

## Status

- Finding: `A-001`
- Source: `architecture-findings.md`
- Status: `planned`
- Owner: `backend`
- Last updated: `2026-04-05`

## Goal

Extract translation and explanation orchestration out of the router into dedicated workflow services, leaving the router responsible only for HTTP validation, dependency wiring, and SSE adaptation.

## Why This Exists

`backend/app/routers/works.py` currently owns six concerns that are not HTTP-specific:

1. **Agent construction** — `_get_work_translation_agent` fetches the work's assigned prompt, resolves the latest version, applies any prompt override, and instantiates `TranslationAgent` directly.
2. **Start/resume decision** — `stream_chapter_translation` determines whether a translation is pending or already complete and transitions status accordingly before any streaming begins.
3. **Per-segment execution loop** — `_translate_segments_stream` is a ~150-line async generator that manages status transitions (`pending → running → completed/idle/error`), iterates segments, builds context windows, streams tokens, persists each completed segment, and handles `asyncio.CancelledError` and general exceptions.
4. **Segment retranslation setup** — `retranslate_segment` captures the existing `tgt` before reset (for instruction-guided flow), resets the segment, and constructs the agent.
5. **Explanation eligibility and caching** — `explain_segment` checks translation status, serves cached explanations short-circuit, assembles surrounding context, streams from the explanation agent, and persists the result.
6. **Domain event shapes** — all SSE payload structures (`translation-status`, `segment-start`, `segment-delta`, `segment-complete`, `translation-complete`, `translation-error`, `explanation-delta`, `explanation-complete`, `explanation-error`) are defined inline in the router.

`TranslationStreamService` and `ExplanationStreamService` exist as lower-level state helpers but do not own any execution logic. The workflow-level logic is entirely unextracted.

This makes the translation and explanation paths untestable without HTTP, and makes future work (concurrency guards, retries, worker queues, alternate execution backends) harder to introduce cleanly.

## Scope

In scope:

- introduce `TranslationWorkflow` service owning agent construction, start/resume decisions, segment execution loop, and status transitions
- introduce `ExplanationWorkflow` service owning eligibility checks, cache short-circuit, context assembly, and explanation persistence
- define typed domain event types yielded by the workflows
- add `SegmentNotFoundError` and `SegmentNotTranslatedError` to `services/exceptions.py`
- slim the router to HTTP validation, `_resolve_prompt_override`, and SSE adaptation
- keep `TranslationStreamService` and `ExplanationStreamService` unchanged as state helpers

Out of scope for this task:

- changing any SSE wire format visible to the frontend
- changing the prompt override token system
- changing the `translation_api_key` injection behavior (A-006 addresses model/provider resolution)
- any frontend changes
- worker queues or durable execution (A-007)
- model registry or provider resolution unification (A-006)
- `models.py` splitting (A-009)

## Target Architecture

```
backend/services/
  translation_workflow.py    ← NEW
  explanation_workflow.py    ← NEW
  translation_stream.py      ← unchanged (segment state helpers)
  explanation_stream.py      ← unchanged (segment context helpers)
  prompt.py                  ← unchanged

backend/app/routers/
  works.py                   ← HTTP adapter only
```

### What stays in the router

- Path and query param parsing
- Work and chapter 404 checks — the router resolves `work` and `chapter` objects and passes them into the workflow; these checks happen before any workflow call
- Domain exception mapping — the router catches `SegmentNotFoundError` and `SegmentNotTranslatedError` raised by workflows and maps them to `HTTPException`; it does not perform segment validation itself
- `_resolve_prompt_override` — decodes a signed token; raises `HTTPException` on bad/expired tokens — HTTP-specific
- `_sse_event()` helper — SSE wire format, transport concern
- `_build_translation_state()` — response shape builder, HTTP-layer concern
- `EventSourceResponse` wrapping
- Session lifecycle: `db = SessionLocal()` and `db.close()` in `finally` blocks

### What moves to workflow services

- `_get_work_translation_agent` → `TranslationWorkflow._resolve_agent`
- `_translate_segments_stream` → `TranslationWorkflow._run_segment_loop`
- chapter translation start/resume logic in `stream_chapter_translation` → `TranslationWorkflow.start_or_resume`
- segment reset, agent construction, context loading in `retranslate_segment` → `TranslationWorkflow.retranslate_segment`
- eligibility check, cache short-circuit, context assembly, explanation persistence in `explain_segment` → `ExplanationWorkflow.explain_segment`
- cache clear + same generation path in `regenerate_explanation` → `ExplanationWorkflow.explain_segment(force=True)`

## Domain Event Types

Workflow methods yield typed event dataclasses rather than raw SSE dicts. The router maps these to `_sse_event()` calls. This decouples workflows from the SSE wire format and makes them independently testable.

### Translation events

```python
# backend/services/translation_workflow.py

@dataclass
class TranslationStatusEvent:
    chapter_translation_id: int
    status: str

@dataclass
class SegmentStartEvent:
    chapter_translation_id: int
    segment_id: int
    order_index: int
    start: int
    end: int
    src: str

@dataclass
class SegmentDeltaEvent:
    chapter_translation_id: int
    segment_id: int
    order_index: int
    delta: str

@dataclass
class SegmentCompleteEvent:
    chapter_translation_id: int
    segment_id: int
    order_index: int
    text: str

@dataclass
class TranslationCompleteEvent:
    chapter_translation_id: int
    status: str

@dataclass
class TranslationErrorEvent:
    chapter_translation_id: int
    error: str
    segment_id: int | None = None
    order_index: int | None = None

TranslationEvent = Union[
    TranslationStatusEvent,
    SegmentStartEvent,
    SegmentDeltaEvent,
    SegmentCompleteEvent,
    TranslationCompleteEvent,
    TranslationErrorEvent,
]
```

### Explanation events

```python
# backend/services/explanation_workflow.py

@dataclass
class ExplanationDeltaEvent:
    segment_id: int
    delta: str

@dataclass
class ExplanationCompleteEvent:
    segment_id: int
    explanation: str

@dataclass
class ExplanationErrorEvent:
    segment_id: int
    error: str

ExplanationEvent = Union[
    ExplanationDeltaEvent,
    ExplanationCompleteEvent,
    ExplanationErrorEvent,
]
```

## Router SSE Mapping

The router maps typed domain events to SSE names and payload dicts via a local mapping function. This keeps the SSE contract stable and in one place.

```python
def _translation_event_to_sse(event: TranslationEvent) -> dict:
    match event:
        case TranslationStatusEvent():
            return _sse_event("translation-status", {...})
        case SegmentStartEvent():
            return _sse_event("segment-start", {...})
        ...

def _explanation_event_to_sse(event: ExplanationEvent) -> dict:
    match event:
        case ExplanationDeltaEvent():
            return _sse_event("explanation-delta", {...})
        ...
```

## New Service Interfaces

### `TranslationWorkflow`

```python
class TranslationWorkflow:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._stream_service = TranslationStreamService(db)
        self._prompt_service = PromptService(db)

    def _resolve_agent(
        self,
        work_id: int,
        prompt_override: dict | None,
    ) -> TranslationAgent:
        """
        Resolve and construct a TranslationAgent for the given work.

        Mirrors the current _get_work_translation_agent logic verbatim:
        - fetches the work's assigned prompt
        - fetches the latest prompt version
        - applies prompt_override (template and model) if provided
        - falls back to settings.translation_model and settings.translation_api_key
          (preserves existing behavior; A-006 will unify provider resolution later)
        """

    async def start_or_resume(
        self,
        chapter: Chapter,
        work_id: int,
        *,
        prompt_override: dict | None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[TranslationEvent, None]:
        """
        Start a new chapter translation or resume a pending one.

        - get_or_create_translation + ensure_segments
        - if no pending segments: transition to completed and yield TranslationCompleteEvent
        - otherwise: resolve agent, collect segments_to_translate, yield from _run_segment_loop
        """

    async def retranslate_segment(
        self,
        chapter: Chapter,
        segment_id: int,
        work_id: int,
        *,
        prompt_override: dict | None,
        instruction: str | None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[TranslationEvent, None]:
        """
        Retranslate a single segment.

        - fetch segment, verify it belongs to the chapter translation
        - raise SegmentNotFoundError if missing
        - capture current_tgt if instruction is provided (for guided retranslation)
        - reset the segment
        - resolve agent, load all_segments for context window
        - yield from _run_segment_loop with is_single_segment=True
        """

    async def _run_segment_loop(
        self,
        agent: TranslationAgent,
        translation: ChapterTranslation,
        segments_to_translate: list[TranslationSegment],
        all_segments: list[TranslationSegment],
        chapter_text: str,
        work_id: int,
        *,
        is_single_segment: bool,
        instruction: str | None,
        current_translation: str | None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[TranslationEvent, None]:
        """
        Executes the per-segment translation loop.

        Mirrors the current _translate_segments_stream logic verbatim:
        - if not is_single_segment: set status to running, yield TranslationStatusEvent
        - for each segment: yield SegmentStartEvent, stream deltas, persist tgt, yield SegmentCompleteEvent
        - call is_disconnected() on each delta and between segments; raise CancelledError if True
        - on asyncio.CancelledError: set status to idle
        - on exception: set status to error, yield TranslationErrorEvent
        - on success (not is_single_segment): set status to completed
        - always yield TranslationCompleteEvent on success
        """
```

### `ExplanationWorkflow`

```python
class ExplanationWorkflow:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._explanation_service = ExplanationStreamService(db)
        self._translation_service = TranslationStreamService(db)

    async def explain_segment(
        self,
        chapter: Chapter,
        segment_id: int,
        *,
        force: bool = False,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[ExplanationEvent, None]:
        """
        Generate or return cached explanation for a translated segment.

        When force=False (default — explain path):
        - fetch segment, verify it belongs to the chapter translation
        - raise SegmentNotFoundError if missing
        - raise SegmentNotTranslatedError if not translated
        - if segment.explanation cached: yield ExplanationDeltaEvent (full text) + ExplanationCompleteEvent, return
        - otherwise: fall through to generation

        When force=True (regenerate path):
        - same preflight checks
        - clear existing explanation via ExplanationStreamService before generating
        - skip cache check entirely

        Both paths:
        - assemble preceding_segments and following_segments via ExplanationStreamService
        - get explanation agent
        - stream chunks, yielding ExplanationDeltaEvent per chunk; call is_disconnected() per chunk
        - on completion: save explanation via ExplanationStreamService, yield ExplanationCompleteEvent
        - on asyncio.CancelledError: re-raise (caller handles SSE teardown)
        - on exception: yield ExplanationErrorEvent
        """
```

## New Exceptions

Add to `backend/services/exceptions.py`:

```python
class SegmentNotFoundError(NotFoundError):
    """Raised when a translation segment lookup fails."""

class SegmentNotTranslatedError(ServiceError):
    """Raised when an explanation is requested for an untranslated segment."""
```

The router catches these and maps them to `HTTPException`:

```python
except SegmentNotFoundError:
    raise HTTPException(status_code=404, detail="segment not found") from None
except SegmentNotTranslatedError:
    raise HTTPException(status_code=400, detail="segment is not translated") from None
```

## Slimmed Router Endpoints

After the migration, each streaming endpoint is a thin adapter:

### `stream_chapter_translation`

```python
@router.get("/{work_id}/chapters/{chapter_id}/translate/stream")
async def stream_chapter_translation(work_id, chapter_id, request, prompt_override_token=None):
    db = SessionLocal()
    # 404 checks: work, chapter, membership
    prompt_override = _resolve_prompt_override(prompt_override_token, work_id, chapter_id)
    workflow = TranslationWorkflow(db)

    async def event_generator():
        try:
            async for event in workflow.start_or_resume(
                chapter, work_id,
                prompt_override=prompt_override,
                is_disconnected=request.is_disconnected,
            ):
                yield _translation_event_to_sse(event)
        finally:
            db.close()

    return EventSourceResponse(event_generator())
```

### `retranslate_segment`

```python
@router.get("/{work_id}/chapters/{chapter_id}/segments/{segment_id}/retranslate/stream")
async def retranslate_segment(work_id, chapter_id, segment_id, request,
                              prompt_override_token=None, instruction=None):
    db = SessionLocal()
    # 404 checks: work, chapter, membership
    prompt_override = _resolve_prompt_override(prompt_override_token, work_id, chapter_id)
    workflow = TranslationWorkflow(db)

    async def event_generator():
        try:
            async for event in workflow.retranslate_segment(
                chapter, segment_id, work_id,
                prompt_override=prompt_override,
                instruction=instruction,
                is_disconnected=request.is_disconnected,
            ):
                yield _translation_event_to_sse(event)
        except SegmentNotFoundError:
            raise HTTPException(status_code=404, detail="segment not found") from None
        finally:
            db.close()

    return EventSourceResponse(event_generator())
```

### `explain_segment`

```python
@router.get("/{work_id}/chapters/{chapter_id}/segments/{segment_id}/explain/stream")
async def explain_segment(work_id, chapter_id, segment_id, request):
    db = SessionLocal()
    # 404 checks: work, chapter, membership
    workflow = ExplanationWorkflow(db)

    try:
        # Eligibility checks happen before returning EventSourceResponse
        # so HTTP 400/404 can be raised normally
        segment = workflow.preflight_check(chapter, segment_id)
    except SegmentNotFoundError:
        db.close()
        raise HTTPException(status_code=404, detail="segment not found") from None
    except SegmentNotTranslatedError:
        db.close()
        raise HTTPException(status_code=400, detail="segment is not translated") from None

    async def event_generator():
        try:
            async for event in workflow.explain_segment(
                chapter, segment_id, is_disconnected=request.is_disconnected
            ):
                yield _explanation_event_to_sse(event)
        finally:
            db.close()

    return EventSourceResponse(event_generator())
```

### `regenerate_explanation`

```python
@router.post("/{work_id}/chapters/{chapter_id}/segments/{segment_id}/regenerate-explanation")
async def regenerate_explanation(work_id, chapter_id, segment_id, request):
    db = SessionLocal()
    # 404 checks: work, chapter, membership
    workflow = ExplanationWorkflow(db)

    try:
        workflow.preflight_check(chapter, segment_id)
    except SegmentNotFoundError:
        db.close()
        raise HTTPException(status_code=404, detail="segment not found") from None
    except SegmentNotTranslatedError:
        db.close()
        raise HTTPException(status_code=400, detail="segment is not translated") from None

    async def event_generator():
        try:
            async for event in workflow.explain_segment(
                chapter, segment_id,
                force=True,
                is_disconnected=request.is_disconnected,
            ):
                yield _explanation_event_to_sse(event)
        finally:
            db.close()

    return EventSourceResponse(event_generator())
```

Note: `preflight_check` is a synchronous method on `ExplanationWorkflow` that validates segment existence and translated state before the SSE response is opened. This avoids the need to raise `HTTPException` from inside an async generator.

## Router Helpers to Remove

Once the three streaming endpoints are migrated, delete from `works.py`:

- `_get_work_translation_agent` (moved to `TranslationWorkflow._resolve_agent`)
- `_translate_segments_stream` (moved to `TranslationWorkflow._run_segment_loop`)

Keep:

- `_resolve_prompt_override`
- `_sse_event`
- `_build_translation_state`
- `_get_completed_translation_chapter_ids`
- `_translation_event_to_sse` (new addition)
- `_explanation_event_to_sse` (new addition)

## Phases

### Phase 1 — Domain exceptions and event types

Files changed:

- `backend/services/exceptions.py` — add `SegmentNotFoundError`, `SegmentNotTranslatedError`
- `backend/services/translation_workflow.py` — create file, define dataclasses and `TranslationEvent` union, stub `TranslationWorkflow` class with `__init__`
- `backend/services/explanation_workflow.py` — create file, define dataclasses and `ExplanationEvent` union, stub `ExplanationWorkflow` class with `__init__`

Deliverable:

- new service files exist and import cleanly; no behavior changes

### Phase 2 — Implement `TranslationWorkflow._resolve_agent`

Move `_get_work_translation_agent` logic verbatim into `TranslationWorkflow._resolve_agent`.

Notes:

- preserves `settings.translation_api_key` injection as-is (A-006 will replace this)
- prompt override model/template logic moves unchanged
- no behavior changes

Deliverable:

- `_resolve_agent` is implemented and covered by a unit test that mocks `PromptService` and `settings`

### Phase 3 — Implement `TranslationWorkflow._run_segment_loop`

Move `_translate_segments_stream` logic verbatim into `_run_segment_loop`, replacing inline `_sse_event()` calls with typed event yields.

Notes:

- the `is_single_segment` flag and `instruction`/`current_translation` parameters carry over unchanged
- status transition logic (`running`, `completed`, `idle`, `error`) moves unchanged
- `asyncio.CancelledError` handling moves unchanged
- disconnect checks replace `await request.is_disconnected()` with `await is_disconnected()`

Deliverable:

- `_run_segment_loop` implemented; no router changes yet; existing behavior is preserved

### Phase 4 — Implement `TranslationWorkflow.start_or_resume`

Move the orchestration logic from `stream_chapter_translation` (lines 744–809 of the current router) into `start_or_resume`:

- `get_or_create_translation` + `ensure_segments`
- check if any pending segments remain
- if already complete: transition to `completed`, yield `TranslationCompleteEvent`, return
- resolve agent via `_resolve_agent`
- collect `segments_to_translate`
- yield from `_run_segment_loop`

Deliverable:

- `start_or_resume` implemented; no router changes yet

### Phase 5 — Implement `TranslationWorkflow.retranslate_segment`

Move the orchestration logic from `retranslate_segment` (lines 816–917) into the workflow:

- fetch segment from DB, verify `chapter_translation_id` matches
- raise `SegmentNotFoundError` if missing
- capture `current_tgt` if `instruction` provided
- call `reset_segment`
- resolve agent
- load `all_segments` for context
- yield from `_run_segment_loop` with `is_single_segment=True`

Deliverable:

- `retranslate_segment` implemented on `TranslationWorkflow`

### Phase 6 — Implement `ExplanationWorkflow`

Move the orchestration logic from both `explain_segment` (lines 920–1107) and `regenerate_explanation` (lines 1112–1281) into `ExplanationWorkflow`.

Both router endpoints share identical generation logic; the only differences are the cache check and the cache clear before generation. Consolidate into one method with a `force` flag rather than two separate methods.

- `preflight_check(chapter, segment_id)` — synchronous; fetches segment, validates translated state, returns or raises domain exceptions; called by both router endpoints before opening the SSE response
- `explain_segment(chapter, segment_id, *, force, is_disconnected)` — async generator:
  - `force=False`: if `segment.explanation` cached, yield cached events and return
  - `force=True`: call `clear_explanation` before proceeding
  - assemble preceding/following context via `ExplanationStreamService`
  - get explanation agent
  - stream, yielding `ExplanationDeltaEvent` per chunk
  - save explanation, yield `ExplanationCompleteEvent`
  - on `asyncio.CancelledError`: re-raise
  - on exception: yield `ExplanationErrorEvent`

Deliverable:

- `ExplanationWorkflow` implemented and covers both the explain and regenerate paths

### Phase 7 — Wire router to workflows

Add `_translation_event_to_sse` and `_explanation_event_to_sse` mapping functions to the router.

Replace the four streaming endpoint bodies with the thin adapter pattern.

Remove `_get_work_translation_agent` and `_translate_segments_stream` from `works.py`.

Deliverable:

- router slimmed; all three streaming endpoints delegate to workflow services
- SSE wire format is unchanged end-to-end

### Phase 8 — Workflow-level event sequence tests

The SSE event contract is the primary risk surface for this refactor. The router tests that exist today go through the full HTTP stack and assert DB state after the fact; they do not verify the event sequence directly. Before wiring the router (Phase 7), write tests that drive the workflow methods in isolation and assert event sequences. This catches regressions in the event contract without needing HTTP.

Test location: `backend/tests/test_translation_workflow.py` and `backend/tests/test_explanation_workflow.py`.

Test harness pattern:

- construct the workflow with a real in-memory SQLite session (same pattern as conftest)
- supply a mock agent whose `stream_segment` or `stream_explanation` yields controlled token sequences
- pass `is_disconnected=async lambda: False` for normal cases
- collect yielded events into a list and assert on type sequence and field values

#### `TranslationWorkflow` tests

| Test | What it asserts |
|---|---|
| `test_start_or_resume_full_chapter` | event sequence: `TranslationStatusEvent(running)` → one `SegmentStartEvent` + `SegmentDeltaEvent`(s) + `SegmentCompleteEvent` per translatable segment → `TranslationCompleteEvent(completed)`; DB `tgt` values written |
| `test_start_or_resume_already_complete` | no `TranslationStatusEvent`; only `TranslationCompleteEvent(completed)` emitted; no agent called |
| `test_start_or_resume_skips_whitespace_segments` | whitespace-flagged segments produce no `SegmentStartEvent`; translatable segments still translate |
| `test_retranslate_segment` | event sequence: `SegmentStartEvent` → `SegmentDeltaEvent`(s) → `SegmentCompleteEvent` → `TranslationCompleteEvent`; translation-level status does NOT change to `completed` (`is_single_segment=True`); DB `tgt` updated |
| `test_retranslate_segment_with_instruction` | `current_translation` is captured from pre-reset `tgt`; agent receives `instruction` and `current_translation` correctly |
| `test_retranslate_segment_not_found` | raises `SegmentNotFoundError` |
| `test_cancellation_sets_status_idle` | pass `is_disconnected=async lambda: True`; `translation.status` is `idle` after the generator is exhausted; no `TranslationCompleteEvent` emitted |
| `test_agent_error_emits_error_event` | agent raises mid-stream; `TranslationErrorEvent` is yielded with correct `segment_id`; `translation.status` is `error` |
| `test_resolve_agent_uses_work_prompt` | mock `PromptService` returns a prompt with a version; agent constructed with that version's template and model |
| `test_resolve_agent_uses_override` | prompt override dict takes precedence over work prompt; agent constructed with override template and model |
| `test_resolve_agent_falls_back_to_defaults` | no work prompt, no override; agent constructed with `settings.translation_model` |

#### `ExplanationWorkflow` tests

| Test | What it asserts |
|---|---|
| `test_explain_segment_cold` | event sequence: `ExplanationDeltaEvent`(s) → `ExplanationCompleteEvent`; explanation persisted to DB |
| `test_explain_segment_cached` | `segment.explanation` pre-set; event sequence: `ExplanationDeltaEvent(full text)` → `ExplanationCompleteEvent`; agent NOT called |
| `test_explain_segment_force_clears_cache` | `force=True` with pre-set `segment.explanation`; explanation cleared, agent called, fresh explanation saved |
| `test_explain_segment_not_translated_raises` | untranslated segment raises `SegmentNotTranslatedError` from `preflight_check` |
| `test_explain_segment_not_found_raises` | missing segment raises `SegmentNotFoundError` from `preflight_check` |
| `test_explain_cancellation` | `is_disconnected=async lambda: True`; `CancelledError` propagates; explanation NOT saved to DB |
| `test_explain_agent_error_emits_error_event` | agent raises mid-stream; `ExplanationErrorEvent` yielded |

#### Existing HTTP test to extend

`test_stream_chapter_translation_persists_segments` currently asserts that `translation-complete` appears somewhere in the SSE text. Extend it to parse the SSE event stream and assert the full event sequence in order: one `translation-status` event, one `segment-start` + at least one `segment-delta` + one `segment-complete` per translatable segment, followed by `translation-complete`. This test continues to run through the HTTP stack and validates that the router's event mapping is correct end-to-end.

Deliverable:

- all workflow-level event sequence tests pass before Phase 7 lands
- existing HTTP test asserts event sequence, not just presence of terminal event

### Phase 9 — Wire router to workflows, remove dead code

(Previously Phase 7 — deferred until Phase 8 tests are in place.)

Add `_translation_event_to_sse` and `_explanation_event_to_sse` mapping functions to the router.

Replace the four streaming endpoint bodies with the thin adapter pattern.

Remove `_get_work_translation_agent` and `_translate_segments_stream` from `works.py`.

Deliverable:

- router slimmed; all four streaming endpoints delegate to workflow services
- SSE wire format is unchanged end-to-end
- all Phase 8 tests still pass

### Phase 10 — Final verification

- run `just lint` and `just test`
- manual smoke test: stream full chapter translation, retranslation with instruction, explanation (cold and cached), regeneration
- update `architecture-findings.md` A-001 status to `done`

## Suggested Implementation Order

1. exceptions and event type stubs
2. `_resolve_agent`
3. `_run_segment_loop`
4. `start_or_resume`
5. `retranslate_segment`
6. `ExplanationWorkflow` (preflight + explain with `force` flag)
7. write workflow-level event sequence tests; extend existing HTTP test
8. router wiring and dead-code removal
9. lint, full test run, smoke test, status update

## Invariants to Preserve

- SSE event names and payload shapes must not change (frontend depends on them)
- `translation_api_key` injection behavior preserved (A-006 will change this later)
- prompt override logic (`_resolve_prompt_override`) stays in the router
- `is_single_segment` distinction preserved (controls status transitions)
- `asyncio.CancelledError` sets status to `idle` (not `error`)
- explanation cache hit path emits both `explanation-delta` and `explanation-complete`
- `db.close()` remains in `finally` inside the SSE generator, not in the workflow

## Risks

- session lifetime: workflows receive a DB session they do not own; must not call `db.close()` internally
- the `explain_segment` eligibility check must happen before `EventSourceResponse` is opened so that HTTP 400/404 can be raised synchronously — the `preflight_check` split handles this
- the `lru_cache` on `get_explanation_agent()` means the singleton agent is constructed once; this is preserved since workflow code calls `get_explanation_agent()` the same way the router does today

## Open Questions

- Should `TranslationWorkflow` and `ExplanationWorkflow` be registered as FastAPI dependencies, or instantiated directly in endpoint bodies (current pattern for all other services in this router)?
- Should `preflight_check` remain a separate method on `ExplanationWorkflow`, or be inlined into the endpoint before the generator is returned?

## Exit Criteria

This task is complete when:

- `TranslationWorkflow` owns agent construction, start/resume decisions, per-segment loop, and status transitions
- `ExplanationWorkflow` owns eligibility checks, cache short-circuit, context assembly, and explanation persistence
- the router contains no segment-loop logic, no agent construction, and no explanation orchestration
- `_get_work_translation_agent` and `_translate_segments_stream` are deleted from `works.py`
- all four streaming endpoints are thin SSE adapters (`stream_chapter_translation`, `retranslate_segment`, `explain_segment`, `regenerate_explanation`)
- `SegmentNotFoundError` and `SegmentNotTranslatedError` are in `services/exceptions.py`
- workflow-level event sequence tests cover: full chapter translation, already-complete short-circuit, whitespace skip, single-segment retranslation, instruction retranslation, segment-not-found, cancellation (status=idle), agent error, agent construction (work prompt, override, defaults), explain cold, explain cached, explain force, explain not-translated, explain not-found, explain cancellation, explain agent error
- existing HTTP SSE test asserts full event sequence in order, not just terminal event presence
- SSE wire format is identical to before
- `just lint` and `just test` pass
- `architecture-findings.md` A-001 status is updated to `done`
