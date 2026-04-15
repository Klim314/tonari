# Translation Explanation Layer — Current State

## Status

- State: `in progress`
- Started: 2026-04-12
- Last updated: 2026-04-15

## Plan

Implementation plan: [translation-explanation-layer-plan.md](translation-explanation-layer-plan.md)
PRD: [translation-explanation-layer-prd.md](translation-explanation-layer-prd.md)
UI mockup: [translation-explanation-layer-ui-mockup.md](translation-explanation-layer-ui-mockup.md)

## Phase Summary

| Phase | Scope | Status | Commit |
|-------|-------|--------|--------|
| 1 | Schema + backend foundation (models, sentence splitter, segment schema extension) | done | `303b23a` |
| 2 | Structured generation + new API (facet schemas, generator v2, service, workflow v2, 3 SSE endpoints) | done | `d28bf44` |
| 2 (tests) | Sentence splitter tests | done | `020091c` |
| 3 | Explanation Workspace UI (two-panel layout, sentence mode, feature-flagged) | done — follow-up fixes still pending review items | — |
| 4 | Span highlighting + polish | not started | — |
| 5 | Segment analysis mode (lower priority) | not started | — |

## What Shipped in Phase 3

New component tree under `frontend/src/components/chapterDetail/translation/explanation/`:

- [types.ts](../../../frontend/src/components/chapterDetail/translation/explanation/types.ts) — local facet shapes and `FacetsState`.
- [useExplanationV2Flag.ts](../../../frontend/src/components/chapterDetail/translation/explanation/useExplanationV2Flag.ts) — localStorage-backed feature flag; `?explanation_v2=1` URL param enables it.
- [useExplanationArtifact.ts](../../../frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts) — GET cache check, POST start, then `EventSource` SSE; `regenerate()` now uses request-key invalidation so `force=true` is consumed once per artifact key.
- [SourcePane.tsx](../../../frontend/src/components/chapterDetail/translation/explanation/SourcePane.tsx) — source + translation with active-sentence highlighting.
- [FacetRail.tsx](../../../frontend/src/components/chapterDetail/translation/explanation/FacetRail.tsx) — desktop vertical rail / mobile horizontal tabs with status glyphs.
- [FacetContent.tsx](../../../frontend/src/components/chapterDetail/translation/explanation/FacetContent.tsx) — facet renderers plus loading/error states.
- [ExplanationToolbar.tsx](../../../frontend/src/components/chapterDetail/translation/explanation/ExplanationToolbar.tsx) — segment counter, sentence counter, regenerate button.
- [ExplanationWorkspace.tsx](../../../frontend/src/components/chapterDetail/translation/explanation/ExplanationWorkspace.tsx) — full-size Chakra dialog; uses generated chapter-translation SDK/types, keyboard segment nav, and small edge nav buttons.

Wired into [TranslationPanel.tsx](../../../frontend/src/components/chapterDetail/translation/TranslationPanel.tsx): when the flag is on, "Explain" opens `ExplanationWorkspace`; otherwise the old markdown `ExplanationPanel` remains active.

Additional hardening since the initial Phase 3 ship:

- [useChapterTranslationStream.ts](../../../frontend/src/hooks/useChapterTranslationStream.ts), [translation_workflow.py](../../../backend/services/translation_workflow.py), and [translation_stream.py](../../../backend/services/translation_stream.py) now preserve partially streamed segment text across hydrate/resume, mark in-flight rows with a `"partial"` flag, persist text per streamed delta, and clear the partial marker when the segment finishes.
- [explanation_workflow_v2.py](../../../backend/services/explanation_workflow_v2.py) and [explanation_generator_v2.py](../../../backend/agents/explanation_generator_v2.py) now replay persisted facet progress from `payload_json` and skip already-complete facets when a workspace is reopened mid-generation.

Validation this session: `just test tests/test_explanation_workflow.py`, `cd frontend && npx tsc --noEmit`, and `cd frontend && npx biome check src/components/chapterDetail/translation/SegmentsList.tsx` passed.

## Review Status

Phase 3 has multiple review passes recorded in [phase-3/review.md](phase-3/review.md). Earlier explanation-workspace issues were addressed. The latest follow-up delta closes one of the two partial-state integration gaps by blocking explanation on `"partial"` rows in both backend preflight paths and the segment context menu.

Still open after the 2026-04-15 review:

- manual batch edits do not clear the new `"partial"` flag, so a later resume can overwrite an explicit user edit
- `.husky/pre-commit` now adds `lint-staged --no-stash`, which is unrelated to the explanation fix and weakens partial-staging safety for frontend commits

## Next Steps

1. Fix the remaining partial-state integration gap: clear `"partial"` on manual edits and add regression coverage through the batch edit API.
2. Decide whether `.husky/pre-commit` should keep `lint-staged --no-stash`; if not, drop it from this delta.
3. Re-run manual QA with the feature flag enabled (`?explanation_v2=1` or `localStorage.setItem('explanation_v2', '1')`): cache hit, cache miss, regenerate, reopen mid-generation, pause/resume chapter translation mid-segment, manual edit on a paused partial segment, and explain availability on incomplete segments.
4. If QA is clean, decide whether to keep the v2 workspace gated or widen exposure before Phase 4.

## Known Issues

- Navigating away from an in-progress sentence explanation and back can briefly leave two server-side stream tasks alive at once (the original is still awaiting its in-flight LLM call when the new one starts). Worst case is one duplicated LLM call for a single facet; final artifact state is consistent because `update_facet` is last-write-wins per facet row. A true lease/heartbeat to prevent the overlap is deferred.
- `useExplanationArtifact.ts` still uses a hand-typed GET response shape (`ArtifactGetResponse`) instead of generated API types; cleanup debt, not a blocker.

## Open Questions

- Is the transient overlap-window concurrency behaviour acceptable, or do we want a generation lease on the artifact before widening the flag?

## Blockers

- Manual edits still do not clear the `"partial"` flag.
- The unrelated `--no-stash` pre-commit change should be removed or justified separately before this follow-up is treated as ready.
