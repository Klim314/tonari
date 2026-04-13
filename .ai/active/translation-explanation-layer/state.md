# Translation Explanation Layer — Current State

## Status

- State: `in progress`
- Started: 2026-04-12
- Last updated: 2026-04-13

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
| 3 | Explanation Workspace UI (two-panel layout, sentence mode, feature-flagged) | done — follow-up fixes still open | — |
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

Validation: `just lint-web` and `just typecheck` pass.

## Review Status

Phase 3 now has four review passes recorded in [phase-3/review.md](phase-3/review.md).

Addressed from earlier reviews:

- sticky regenerate invalidation bug in `useExplanationArtifact.ts`
- transient SSE reconnects incorrectly surfacing as errors
- ad-hoc chapter translation response typing in `ExplanationWorkspace.tsx`
- redundant initial-segment reset effect in `ExplanationWorkspace.tsx`
- missing `sentences.length > 0` fetch guard
- edge-overlay navigation interfering with selection
- dead facet-rail `"generating"` UI branch
- leftover debug logging in `TranslationPanel.tsx`

Still open after the latest re-review:

- reopening the workspace while an explanation artifact is still `pending` / `generating` can still restart generation instead of reattaching to the in-progress artifact
- the frontend SSE error handler still expects `error`, while the backend v2 stream emits `message`, so real backend failure details are lost in the UI

## Next Steps

1. Fix the SSE error payload contract mismatch between `backend/app/routers/works.py` and `useExplanationArtifact.ts`.
2. Decide whether Phase 3 must support true reopen/resume for in-progress artifacts now, or explicitly defer it to Phase 4 with that risk called out.
3. Re-run manual QA with the feature flag enabled (`?explanation_v2=1` or `localStorage.setItem('explanation_v2', '1')`): cache hit, cache miss, regenerate, reopen mid-generation, keyboard nav, and facet switching.
4. If the follow-up fixes land cleanly, decide whether to keep the v2 workspace gated or widen exposure before Phase 4.

## Known Issues

- Reopening a still-running sentence explanation does not yet hydrate partial facet progress or attach to the existing run.
- The hook still uses a hand-typed GET response shape (`ArtifactGetResponse`) even though generated API types now exist; this is cleanup debt, not a release blocker by itself.

## Open Questions

- Should in-progress artifact replay / attach be treated as required before widening the flag, or is it acceptable to defer until Phase 4?
- Do we want the SSE error payload to standardize on `error` for parity with the older explanation stream, or switch the frontend to `message` for v2 only?

## Blockers

- None.
