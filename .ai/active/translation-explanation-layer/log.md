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

## 2026-04-15 — Review pass on detached explanation generation follow-up

- Reviewed the current backend delta that moves sentence explanations from request-scoped SSE generation into detached background tasks backed by a process-local registry.
- Appended a new `Codex` block to `phase-3/review.md`.
- Added two new important findings:
  - detached explanation runs can now finish and cache artifacts for stale `segment.tgt` text if the translation changes after the POST starts generation, because the artifact key is not versioned by translation state and translation edits do not invalidate `translation_explanations`
  - some fatal producer exits (for example missing setup data before facet generation) emit/log an error but do not persist `status="error"` on the artifact, leaving the row stuck in a non-terminal state
- Refreshed `state.md` so the active blocker list now includes both detached-generation issues in addition to the earlier partial-edit and pre-commit concerns.

## 2026-04-16 — Phase 4 kickoff audit

- Decided to move past remaining Phase 3 follow-ups (partial-flag-on-edit, stale detached explanations, producer setup errors) and start Phase 4 work. Those items remain tracked in `state.md` / `backlog.md`.
- Audited existing code against the Phase 4 checklist before planning new work. Several items were already landed during Phase 3 implementation, so scope is smaller than the plan implies:
  - **Edge-click navigation** — already shipped as `EdgeNav` in `ExplanationWorkspace.tsx` (desktop-only chevrons at left/right of the reading pane).
  - **Mobile tab rail** — already shipped; `FacetRail` renders in `orientation="horizontal"` above `FacetContent` on mobile.
  - **Cache status badge** — partial; `statusLabel` in `ExplanationWorkspace.tsx` already emits `"cached · sparse"` / `"generating..."` / `"loading..."` / `"error"` and renders through `FacetSidebar`. Still density-unaware and desktop-only.
- Remaining Phase 4 work:
  - **Span highlighting on card click** — schema fields `source_span_start` / `source_span_end` exist on `VocabularyItem` and `GrammarPoint` in `backend/app/explanation_schemas.py`, and the frontend `types.ts` carries them, but `FacetContent.tsx` only uses them as part of a React key. No click handler, no active-span state, no wiring into `SourcePane`.
  - **Mobile bottom action bar** — Prev/Next/Regenerate still live in the toolbar on all breakpoints; plan calls for a bottom bar on mobile.
  - **SSE reconnect** — `useExplanationArtifact.ts` still closes on error with no automatic retry (noted as deferred in the original Phase 3 log entry).
  - **Cache status badge polish** — density-aware labeling and mobile placement.
- **Gating concern for span highlighting:** `SYSTEM_EXPLANATION_V2_SPARSE` / `SYSTEM_EXPLANATION_V2_DENSE` in `backend/agents/prompts.py` do not mention span offsets at all. Structured output via `llm.with_structured_output(schema)` may populate the fields, but the prompts give the LLM no guidance on what character offsets to emit. Before building the highlight UI we need to either (a) verify empirically that an existing artifact has populated spans, or (b) update the v2 system prompts to explicitly instruct the LLM to emit character offsets into the `<sentence>` text.

## 2026-04-16 — Explanation quality review

- Performed a non-technical review of the current explanation system focused on output quality and selection logic rather than transport or storage.
- Read the active task state plus the current v2 prompt/schema/generator flow:
  - `backend/agents/prompts.py`
  - `backend/agents/explanation_generator_v2.py`
  - `backend/app/explanation_schemas.py`
  - `frontend/src/components/chapterDetail/translation/explanation/FacetContent.tsx`
  - PRD / plan / UI mockup docs under `.ai/active/translation-explanation-layer/`
- Wrote findings to `.ai/active/translation-explanation-layer/explanation-quality-review-2026-04-16.md`.
- Main conclusion: the v2 system has the right facet structure, but the current logic is still too generic. The biggest opportunity is to improve what gets selected for explanation, especially in `overview`, `vocabulary`, and `translation_logic`.
- Recommended product-level priorities:
  - move from one shared explanation prompt to facet-specific rubrics
  - make `translation_logic` about discrete decision points instead of a single broad rationale block
  - define true sparse/dense selection rules rather than length differences
  - handle ambiguity and context dependency explicitly
- Updated `state.md` to link the new review doc and include the quality-rubric work as a follow-up track alongside the ongoing Phase 4 UI work.

## 2026-04-16 — Facet rubric draft v1

- Turned the quality review into a concrete rubric artifact at `.ai/active/translation-explanation-layer/facet-rubrics-v1-2026-04-16.md`.
- Defined rubric rules for the four current facets:
  - `overview`
  - `vocabulary`
  - `grammar`
  - `translation_logic`
- Added shared guidance for:
  - global explanation rules
  - cross-facet boundaries to reduce overlap
  - sparse vs dense selection policy
  - comparison criteria for later rubric variants
- Updated `state.md` to link the new rubric artifact and treat it as the baseline document to compare against future rubric attempts before moving into prompt drafting.

## 2026-04-16 — Facet prompt drafts v1

- Created `.ai/active/translation-explanation-layer/facet-prompts/` to hold prompt drafts outside the production codepath.
- Added a folder index at `.ai/active/translation-explanation-layer/facet-prompts/README.md`.
- Added four Codex-authored prompt draft files:
  - `overview-prompt-v1-codex-2026-04-16.md`
  - `vocabulary-prompt-v1-codex-2026-04-16.md`
  - `grammar-prompt-v1-codex-2026-04-16.md`
  - `translation-logic-prompt-v1-codex-2026-04-16.md`
- Each file is explicitly marked with `Created by: Codex` so future variants can be compared cleanly.
- The prompt drafts are based on `facet-rubrics-v1-2026-04-16.md` and are intentionally stored as design artifacts rather than integrated prompt code.
- Updated `state.md` to link the prompt-draft folder and track comparison against alternate prompt sets before any runtime prompt rewrite.

## 2026-04-17 — Facet prompt comparison pass

- Reviewed the four Codex-authored prompt drafts against:
  - the current schema in `backend/app/explanation_schemas.py`
  - the rubric baseline in `.ai/active/translation-explanation-layer/facet-rubrics-v1-2026-04-16.md`
  - the alternate prompt-design docs already present in `.ai/active/translation-explanation-layer/facet-prompts/`
- Wrote the comparison artifact to `.ai/active/translation-explanation-layer/facet-prompts/facet-prompt-comparison-codex-vs-alt-2026-04-17.md`.
- Main conclusions:
  - the Codex drafts are concise and directionally correct, but mostly rubric-shaped rather than schema-shaped
  - `vocabulary` and `grammar` are closest to runtime viability but need explicit field contracts and span-offset instructions
  - `overview` needs stronger anti-paraphrase constraints
  - `translation_logic` has the best product direction but is blocked more by schema mismatch than by prompt wording
- Updated `state.md` to link the comparison artifact and convert the old "compare prompt drafts" next step into concrete revision decisions.
