# Translation Explanation Layer — Session Log

Append-only. Each session adds an entry. Only consult when you need to understand past decisions.

## 2026-04-12 — Phase 1: schema and backend foundation

- Created persistent task workspace in `.ai/active/translation-explanation-layer/` (retroactively, 2026-04-13).
- Discussed data model before migrating. Original plan had a separate `translation_explanation_spans` table keyed by sentence spans.
- Decision: drop the spans table. Every explanation is anchored to a segment; `span_start` / `span_end` live directly on `translation_explanations` as nullable columns. `NULL` means segment-level explanation.
- Cache key enforced at the DB level via unique constraint on `(anchor_segment_id, span_start, span_end, density)`.
- Moved `sentence_splitter.py` under `backend/app/utils/` and created the `utils/` package.
- Built `GreedySentenceSplitter` with Japanese terminators (`。？！…` plus multi-char sequences like `？！`, `！！`, `…。`).
- Extended `TranslationSegmentOut` with a `sentences: list[SentenceSpanOut]` field populated by the splitter.
- Regenerated Alembic migration using the autogenerator (deleted hand-written draft).
- Committed as `303b23a` ("phase 1: models").

## 2026-04-12 — Phase 2: structured generation and API

- Added facet schemas in `backend/app/explanation_schemas.py` covering overview, vocabulary, grammar, and translation logic, plus the `FacetEntry` / `ArtifactPayload` envelope and API schemas for the three new endpoints.
- Added `SYSTEM_EXPLANATION_V2_SPARSE` / `SYSTEM_EXPLANATION_V2_DENSE` prompts in `backend/agents/prompts.py`.
- Built `ExplanationGeneratorV2` (`backend/agents/explanation_generator_v2.py`) yielding one complete Pydantic facet at a time via `llm.with_structured_output(schema)`. Initial implementation cached a runnable keyed by `(facet_type, system_prompt[:20])`; fixed during review to cache only `(facet_type → structured_llm)` and pass the system prompt per call. Stub data returned when no API key is configured.
- Built `ExplanationService` (`backend/services/explanation_service.py`) for artifact lifecycle.
- Built `ExplanationWorkflowV2` (`backend/services/explanation_workflow_v2.py`) for start/stream orchestration with cache-hit replay.
- Added three new endpoints under `.../sentences/explanation` in `backend/app/routers/works.py`: `GET` (fetch artifact state), `POST` (start/regenerate), SSE stream. Density param typed as `Literal["sparse", "dense"]`. Old explanation endpoints left live during transition.
- Regenerated frontend API client via `just generate-api`.
- Review pass (see `REVIEW.md`) surfaced 10 issues; 9 resolved:
  - C-1 (TOCTOU in `get_or_create`) → fixed with `SELECT … FOR UPDATE` on the segment row.
  - I-1 (`mark_error` data loss) → added `error: str | None` to `ArtifactPayload`.
  - I-1a (partial failures finalized as `complete`) → track `any_facet_error`, call `mark_error` on partial failure, extend cache hit check to `status in ("complete", "error")`, replay errored facets as `ArtifactErrorEvent`.
  - I-1b (spans not validated) → added `SpanValidationError` and `validate_span()`; called from `start()` and the stream endpoint, returning 400 on failure.
  - I-3, I-4, M-1, M-2, M-3 → resolved.
  - I-2 (null guard on `segment`) → deferred, low-risk TOCTOU with segment deletion.
  - I-5 (sync DB in async path) → acknowledged / deferred; consistent with existing codebase patterns.
- Extracted `create_llm` / `render_block` to module-level in `agents/base_agent.py` (from the review).
- Committed as `d28bf44` ("phase 2: structured explanation generator and API"): 19 files, +1628 / −123.

## 2026-04-13 — Session closeout

- Created `.ai/active/translation-explanation-layer/state.md` and `log.md` per `.ai/shared/instructions.md`.
- Moved `REVIEW.md` → `archive/phase-2-review.md` under the task dir.
- Committed `backend/tests/test_sentence_splitter.py` as `020091c` ("phase 2: tests for sentence splitter").
- Moved the task-specific docs (`translation-explanation-layer-{plan,prd,ui-mockup}.md`) out of `docs/prds/` and into the task dir root; updated `state.md` links.
- Next session: Phase 3 (Explanation Workspace UI).

## 2026-04-13 — Phase 3: Explanation Workspace UI (feature-flagged)

- Kept the old markdown `ExplanationPanel` live; new workspace gated behind a localStorage flag (`explanation_v2`) that can be flipped per-browser via `?explanation_v2=1` URL param. Default is old panel, per user direction.
- Chose sentence-only UI: no `Unit: [Sentence ▾]` selector (segment mode is Phase 5), no Sparse/Dense toggle (locked to sparse).
- New component tree under `frontend/src/components/chapterDetail/translation/explanation/`:
  - `types.ts` — typed facet shapes (`OverviewData`, `VocabularyData`, `GrammarData`, `TranslationLogicData`) and `FacetsState`.
  - `useExplanationV2Flag.ts` — localStorage + URL-param feature flag.
  - `useExplanationArtifact.ts` — GET → (cache-miss) POST → `EventSource` SSE. Facet-complete events populate per-facet state; facet-level error events set per-facet error; artifact-level completion toggles workspace status.
  - `SourcePane.tsx` — source + translation blocks with the active sentence highlighted via `<mark>` (`bg="yellow.subtle"`) over the source.
  - `FacetRail.tsx` — desktop vertical rail / mobile horizontal tabs, per-facet status glyph (dot / spinner).
  - `FacetContent.tsx` — per-facet renderers + skeleton + error states. Vocabulary uses a 2-col card grid; grammar uses stacked cards; translation logic uses labeled cards.
  - `ExplanationToolbar.tsx` — segment counter, sentence counter with inline prev/next, Regenerate button.
  - `ExplanationWorkspace.tsx` — full-size `DialogRoot` shell. Fetches `/works/{w}/chapters/{c}/translation` for the segment list + sentence spans. Falls back to a single whole-segment span if the backend returns no sentences. Keyboard `Left/Right` moves between segments, subtle edge-click targets on the reading pane do the same. Both default to first sentence on segment change.
- Wired the workspace into `TranslationPanel.tsx` alongside the existing panel behind `useExplanationV2Flag`.
- Deviations from plan worth noting on future work: staleness indicator not implemented (backend has no snapshot hash yet); density toggle deferred; SSE reconnect not yet robust (closes on error, no auto-retry) — all slated for Phase 4.
- Not committed yet; awaiting user QA with the flag enabled.

## 2026-04-13 — Phase 3 second review pass

- Merged a second review into `.ai/active/translation-explanation-layer/phase-3/review.md` instead of replacing the earlier Opus review.
- Confirmed `just lint-web` and `just typecheck` pass.
- Added three Codex findings to the review:
  - medium: reopening the workspace while generation is still in progress can restart generation instead of hydrating and resuming the existing artifact
  - low: edge-click navigation overlays interfere with text selection near the pane edges
  - low: facet-rail `"generating"` spinner path is currently unreachable because per-facet state never enters `"generating"`
- Updated `state.md` so Phase 3 is now tracked as pending review fixes plus manual QA, not just manual QA.

## 2026-04-13 — Phase 3 cleanliness review pass

- Performed another review focused on code cleanliness, structure, and simplicity rather than user-visible behavior.
- Appended a new `Codex` block to `phase-3/review.md` instead of editing prior review notes.
- Added three structural follow-ups:
  - simplify the `regenerateToken`/`lastProcessedTokenRef` handshake in `useExplanationArtifact.ts`
  - replace the local chapter-translation response interface in `ExplanationWorkspace.tsx` with generated SDK types
  - remove the split ownership of initial segment selection between `TranslationPanel.tsx` and `ExplanationWorkspace.tsx`
- Added two smaller cleanup notes:
  - remove leftover `console.info` instrumentation from `handleSegmentExplain()`
  - either make per-facet `"generating"` real or remove the dead branch from `FacetRail`
- Refreshed `state.md` so the next implementation pass can treat these as part of the Phase 3 cleanup queue.

## 2026-04-13 — Phase 3 regenerate invalidation fix

- Replaced the old `regenerateToken` / `lastProcessedTokenRef` force logic in `frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts` with key-based invalidation.
- The hook now derives a stable request key from `(segmentId, spanStart, spanEnd, density)`.
- `regenerate()` stores the current request key in a ref, bumps an invalidation nonce to retrigger the effect, and the effect consumes `force=true` exactly once for that key before reopening the SSE stream.
- This fixes the earlier bug where one regenerate could cause later segment/sentence navigation to keep bypassing cache reads.
- Validation passed: `just lint-web` and `just typecheck`.

## 2026-04-13 — Phase 3 follow-up re-review

- Re-reviewed the current PR against the accumulated Phase 3 review notes.
- Confirmed the follow-up branch has addressed the earlier sticky regenerate bug, transient SSE reconnect handling, generated SDK typing in `ExplanationWorkspace.tsx`, the redundant reset effect, the missing sentence-count fetch guard, the oversized edge nav overlays, the dead facet-rail `"generating"` branch, and the leftover `console.info`.
- Added one new review finding to `phase-3/review.md`: the frontend v2 SSE error handler still expects `error`, but the backend emits `message`, so the workspace drops the real backend error detail and falls back to generic strings.
- Confirmed the earlier medium issue remains open: reopening the workspace while an artifact is still `pending` / `generating` still goes through POST + stream again and can restart generation instead of attaching to the in-progress artifact.
- Re-ran frontend validation: `just lint-web` and `just typecheck` both pass.

## 2026-04-13 — Phase 3 hydration hardening

- Focused on the remaining hydration/regression issue around chapter translation resume behavior.
- Root cause was twofold:
  - backend only persisted `TranslationSegment.tgt` once a segment finished, so disconnecting mid-segment lost the visible partial text
  - frontend `useChapterTranslationStream.ts` cleared `text` on `segment-start`, so a resumed/restarted stream could blank out already hydrated text before new deltas arrived
- Added partial segment persistence in `backend/services/translation_workflow.py` and `backend/services/translation_stream.py`:
  - persist `tgt` on every streamed delta
  - mark incomplete rows with a `"partial"` flag so resume still treats them as pending
  - clear the partial flag once a segment completes
  - exclude partial rows from context-window reuse
- Updated `frontend/src/hooks/useChapterTranslationStream.ts` to:
  - hydrate `"partial"` segments as pending while preserving their current text
  - keep existing text visible when a replacement stream starts
  - replace, not append to, the first delta after a restart/retranslation so text is not duplicated
- Added backend regression coverage in `backend/tests/test_translation_workflow.py` for:
  - disconnect after first delta persists partial text and leaves the segment resumable
  - resumed runs finalize partial segments and clear the partial marker
- Validation:
  - `npm run typecheck` passed
  - `npm run lint -- src/hooks/useChapterTranslationStream.ts` passed
  - `just test` ran; the new translation workflow tests passed, and the suite has one unrelated existing failure in `tests/test_prompts_validation.py::TestPromptVersionValidation::test_create_version_invalid_template_syntax`

## 2026-04-13 — Review pass on partial-state follow-up

- Reviewed the current delta after the partial-translation persistence / hydration changes.
- Re-ran focused backend validation:
  - `just test tests/test_translation_workflow.py` passed
  - `just test tests/test_explanation_workflow.py` passed
- Appended a new `Codex` block to `phase-3/review.md`.
- Added two important findings:
  - partial segments now persist non-empty `tgt`, but explanation preflight and the UI still allow “Explain Translation” on those incomplete rows
  - manual batch edits do not clear the new `"partial"` flag, so resuming translation can overwrite an explicit user edit on a paused partial segment
- Refreshed `state.md` so the current session state now tracks those two items as the remaining blockers for this follow-up delta.

## 2026-04-15 — Review pass on explanation guard follow-up

- Reviewed the current follow-up delta that updates explanation eligibility for partial segments.
- Confirmed the intended fix landed in all three relevant paths:
  - `backend/services/explanation_stream.py` now rejects `PARTIAL_TRANSLATION_FLAG`
  - `backend/services/explanation_workflow_v2.py` now rejects `PARTIAL_TRANSLATION_FLAG`
  - `frontend/src/components/chapterDetail/translation/SegmentsList.tsx` now disables Explain unless the segment status is `completed`
- Validation:
  - `just test tests/test_explanation_workflow.py` passed
  - `cd frontend && npx tsc --noEmit` passed
  - `cd frontend && npx biome check src/components/chapterDetail/translation/SegmentsList.tsx` passed
- Appended a new `Codex` block to `phase-3/review.md`.
- Remaining important finding: manual batch edits still do not clear the `"partial"` flag in `batch_update_segment_translations()`, so user edits on paused partial rows can still be overwritten on resume.
- New unrelated review finding: `.husky/pre-commit` now uses `lint-staged --no-stash`, which weakens partial-staging safety and should be reverted or justified in a separate change.
