# Translation Explanation Layer — Current State

## Status

- State: `in progress`
- Started: 2026-04-12
- Last updated: 2026-04-17

## Plan

Implementation plan: [translation-explanation-layer-plan.md](translation-explanation-layer-plan.md)
PRD: [translation-explanation-layer-prd.md](translation-explanation-layer-prd.md)
UI mockup: [translation-explanation-layer-ui-mockup.md](translation-explanation-layer-ui-mockup.md)
Quality review: [explanation-quality-review-2026-04-16.md](explanation-quality-review-2026-04-16.md)
Facet rubrics v1: [facet-rubrics-v1-2026-04-16.md](facet-rubrics-v1-2026-04-16.md)
Facet prompt drafts: [facet-prompts/README.md](facet-prompts/README.md)
Facet prompt comparison: [facet-prompts/facet-prompt-comparison-codex-vs-alt-2026-04-17.md](facet-prompts/facet-prompt-comparison-codex-vs-alt-2026-04-17.md)

## Phase Summary

| Phase | Scope | Status | Commit |
|-------|-------|--------|--------|
| 1 | Schema + backend foundation (models, sentence splitter, segment schema extension) | done | `303b23a` |
| 2 | Structured generation + new API (facet schemas, generator v2, service, workflow v2, 3 SSE endpoints) | done | `d28bf44` |
| 2 (tests) | Sentence splitter tests | done | `020091c` |
| 3 | Explanation Workspace UI (two-panel layout, sentence mode, feature-flagged) | done — follow-up items deferred to backlog | — |
| 4 | Span highlighting + polish | in progress (kicked off 2026-04-16) | — |
| 5 | Segment analysis mode (lower priority) | not started | — |

## Phase 4 Audit (2026-04-16)

Some Phase 4 items were already completed during Phase 3. Current state per task:

| Task | Status |
|---|---|
| Span highlighting on card click | not started — schema + frontend types carry `source_span_start/end`, but no click handler, no active-span state, no wiring into `SourcePane` |
| Edge-click navigation | done — `EdgeNav` in [ExplanationWorkspace.tsx](../../../frontend/src/components/chapterDetail/translation/explanation/ExplanationWorkspace.tsx) |
| Mobile tab rail | done — `FacetRail` renders horizontal above `FacetContent` on mobile |
| Mobile bottom action bar | not started — Prev/Next/Regenerate still live in the toolbar on all breakpoints |
| Cache status badge | partial — `statusLabel` emits `"cached · sparse"` / `"generating..."` / `"loading..."` / `"error"` via `FacetSidebar`; density-unaware and desktop-only |
| SSE reconnect | not started — `useExplanationArtifact.ts` closes on error with no retry |

### Gating concern — span highlighting

`SYSTEM_EXPLANATION_V2_SPARSE` / `SYSTEM_EXPLANATION_V2_DENSE` in [backend/agents/prompts.py](../../../backend/agents/prompts.py) do not mention span offsets. Structured output may populate `source_span_start` / `source_span_end` opportunistically, but nothing guarantees it. Before building the highlight UI we need to either:

- verify empirically that existing artifacts have populated spans reliably, or
- update the v2 system prompts to explicitly instruct the LLM to emit character offsets into the `<sentence>` text.

## Explanation Quality Review (2026-04-16)

A separate product-quality pass is now captured in [explanation-quality-review-2026-04-16.md](explanation-quality-review-2026-04-16.md).

Main conclusion:

- The v2 layer has the right product structure, but the generation logic is still schema-first rather than learner-first.

Highest-leverage product changes:

- Give each facet its own usefulness rubric instead of one shared generic prompt.
- Redesign `translation_logic` around 2-4 concrete decision points rather than one sentence-wide explanation blob.
- Make `sparse` vs `dense` differ by selection policy, not just output length.
- Treat ambiguity and context dependency as first-class explanation behavior.
- Tighten `overview` so it explains sentence role + translation pressure, not just content.

Current artifact:

- [facet-rubrics-v1-2026-04-16.md](facet-rubrics-v1-2026-04-16.md) defines the first concrete rubric set for `overview`, `vocabulary`, `grammar`, and `translation_logic`, plus cross-facet boundaries and sparse/dense policy.
- [facet-prompts/README.md](facet-prompts/README.md) indexes Codex-authored prompt draft files for the current four facets.
- [facet-prompts/facet-prompt-comparison-codex-vs-alt-2026-04-17.md](facet-prompts/facet-prompt-comparison-codex-vs-alt-2026-04-17.md) compares the Codex prompt drafts against the alternate prompt-design docs already in the folder and identifies the main strengths, weaknesses, and schema gaps per facet.

## What Shipped Earlier in Phase 3

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
- [explanation_generation_registry.py](../../../backend/services/explanation_generation_registry.py), [explanation_workflow_v2.py](../../../backend/services/explanation_workflow_v2.py), and the sentence-explanation endpoints in [works.py](../../../backend/app/routers/works.py) now let explanation generation continue in a detached background task so SSE disconnects do not immediately waste in-flight LLM work.

Latest validation on file: `just test tests/test_explanation_workflow.py`, `cd frontend && npx tsc --noEmit`, and `cd frontend && npx biome check src/components/chapterDetail/translation/SegmentsList.tsx` passed.

## Review Status

Phase 3 has multiple review passes recorded in [phase-3/review.md](phase-3/review.md). Earlier explanation-workspace issues were addressed. Remaining Phase 3 follow-up items are now deferred into Phase 4 / backlog rather than gating Phase 4 kickoff.

## Next Steps (Phase 4)

1. Decide the span-highlighting gating question: inspect a real artifact's vocabulary/grammar items to see whether `source_span_start/end` are populated. If not, update the v2 system prompts in [backend/agents/prompts.py](../../../backend/agents/prompts.py) to instruct the LLM to emit character offsets into the `<sentence>` text.
2. Implement span highlight on card click in `FacetContent.tsx` + `SourcePane.tsx`: single active highlight at a time, deactivates on click-away, driven by `source_span_start/end` on vocabulary and grammar items.
3. Add SSE reconnect to `useExplanationArtifact.ts`: on drop, re-GET the artifact (render completed facets), then re-open the stream for pending facets. No partial-JSON parsing.
4. Mobile bottom action bar: move Prev/Next/Regenerate to a bottom-of-dialog bar at mobile breakpoints; toolbar keeps counters.
5. Cache status badge polish: make it density-aware and surface it on mobile as well as desktop.
6. Manual QA with `?explanation_v2=1`: span click-highlight, mobile layout, SSE drop/reconnect, density labeling.
7. Product-quality follow-up: turn the quality review into a revised facet rubric before deeper prompt/schema work. Prioritize facet-specific selection rules, decision-point-based `translation_logic`, and true sparse/dense policies.
8. Compare `facet-rubrics-v1-2026-04-16.md` against at least one alternative rubric attempt before locking prompt drafts.
9. Turn the prompt comparison into a concrete prompt-revision pass. Highest leverage: `vocabulary` and `grammar` field contracts + span instructions, then `overview` anti-paraphrase hardening.
10. Decide whether `translation_logic` will keep the current blob schema or move to a decision-point schema before further prompt tuning.

## Deferred Work (Phase 3 follow-ups not gating Phase 4)

Tracked in [backlog.md](backlog.md):

- Manual batch edits do not clear the `"partial"` flag, so a later resume can overwrite an explicit user edit.
- `.husky/pre-commit` now adds `lint-staged --no-stash`; unrelated to the explanation fix and weakens partial-staging safety for frontend commits.
- Detached explanation runs can finalize and cache an artifact for stale `segment.tgt` text if the translation changes after the POST starts generation.
- Some fatal detached-producer exits leave the artifact row stuck in `pending` / `generating` instead of persisting `status="error"`.
- Force-reset race in `ExplanationWorkflowV2.start(force=True)` — concurrent `subscribe()` can build `done_facets` from pre-reset `payload_json` and skip facets permanently. Low priority for single-user; revisit with the Redis migration.
- Process-local `GenerationRegistry` — move behind Redis (or DB advisory lock) for multi-worker. Single-worker is a deployment requirement until then.

## Known Issues

- Navigating away from an in-progress sentence explanation and back can briefly leave two server-side stream tasks alive at once (the original is still awaiting its in-flight LLM call when the new one starts). Worst case is one duplicated LLM call for a single facet; final artifact state is consistent because `update_facet` is last-write-wins per facet row. A true lease/heartbeat to prevent the overlap is deferred.
- `useExplanationArtifact.ts` still uses a hand-typed GET response shape (`ArtifactGetResponse`) instead of generated API types; cleanup debt, not a blocker.
- Detached explanation runs are still process-local and unversioned against translation edits, so artifact correctness currently depends on the underlying segment text staying stable for the life of the run.

## Open Questions

- Are the v2 prompts producing populated `source_span_start/end` for vocabulary and grammar items today, or does the prompt need to be updated before the span-highlight UI can land?
- Is the transient overlap-window concurrency behaviour acceptable, or do we want a generation lease on the artifact before widening the flag?

## Blockers

- None for Phase 4 kickoff — the Phase 3 correctness issues above are deferred into the backlog rather than blocking Phase 4.
