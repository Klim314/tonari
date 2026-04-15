# Phase 3 Review

## Reviewer: Opus 4.6 (Review-Agent) — 2026-04-13

**Files reviewed**: `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`, new `frontend/src/components/chapterDetail/translation/explanation/` directory (`ExplanationWorkspace.tsx`, `useExplanationArtifact.ts`, `useExplanationV2Flag.ts`, `ExplanationToolbar.tsx`, `FacetContent.tsx`, `FacetRail.tsx`, `SourcePane.tsx`, `types.ts`), plus PRD/plan/mockup doc deletions (moved into task dir).

**Scope context**: Phase 3 delta, gated behind `?explanation_v2=1` URL flag (persists to localStorage). Old markdown modal remains default. Deliberate omissions per plan: no Unit selector, no density toggle, no staleness indicator, no SSE auto-reconnect — deferred to Phase 4.

### Important

- **[useExplanationArtifact.ts:116]** `const force = regenerateToken > 0;` — once the user clicks Regenerate once in a session, `regenerateToken` stays non-zero, so **every subsequent segment/sentence change forces a fresh generation** and skips the GET cache check. Silently burns LLM tokens on every navigation after the first regenerate.
  → Reset `regenerateToken` to 0 when `segmentId`/`spanStart`/`spanEnd`/`density` change, or track "last-forced key" in a ref cleared after consumption.

- **[useExplanationArtifact.ts:191-198]** `es.onerror` flips status to `"error"` on any non-`CLOSED` readyState, but SSE `onerror` also fires on transient reconnects (`readyState === CONNECTING`). Result: network blips surface as false errors even when the stream eventually completes via `explanation-complete`.
  → Track a "completed" flag in a ref; only treat `CLOSED` without prior `explanation-complete` as real error; ignore `CONNECTING`. (Phase 4 auto-reconnect deferral acknowledged, but this actively misreports today rather than silently ignoring.)

- **[ExplanationWorkspace.tsx:90-106]** Hand-rolled `client.get<ChapterTranslationResponse>(...)` call with an ad-hoc local interface bypasses the generated SDK (`sdk.gen.ts`) for an endpoint that is already typed there. Schema drift risk — backend changes won't surface as type errors.
  → Use the generated typed SDK function for chapter translation and drop the local `ChapterTranslationResponse` interface.

- **[ExplanationWorkspace.tsx:65-75]** Reset-on-`isOpen` effect re-snaps `segmentId` to `initialSegmentId`, but the parent already forces remount via `key={explanationSegmentId}`. Redundant today and fragile if the parent's key contract ever changes.
  → Pick one model: internal `segmentId` state *or* parent-controlled via `key`. Mixing the two invites confusion.

- **[ExplanationWorkspace.tsx:156-169]** `canFetch` requires `currentSegment.tgt` but not `sentences.length > 0`. In a race where `canFetch` is true but `activeSentence` is still stale/undefined, the fetch posts `spanStart: 0, spanEnd: 1` (fallback values) which may not match a real sentence.
  → Add `sentences.length > 0` to the `canFetch` guard to make the invariant explicit.

### Minor

- **[ExplanationWorkspace.tsx:340-370]** Three overlapping segment-navigation affordances on one screen (edge strips, header chevrons, arrow keys). Consider collapsing to one or two.
- **[ExplanationWorkspace.tsx:420-423]** Inline default `{ status: "pending", data: null, error: null }` when `facets[activeFacet]` is missing — dead fallback, `emptyFacets()` guarantees all four keys exist.
- **[FacetContent.tsx:52-61]** Switch lacks a `default: return null` — TypeScript exhaustiveness covers this, but an explicit default is safer.
- **[useExplanationArtifact.ts:191]** Mixed functional updates (`setStatus((prev) => ...)`) and direct calls (`setStatus("error")`) in adjacent branches — inconsistent, harder to reason about the error path.
- **[useExplanationV2Flag.ts:16]** Stores `"0"` into localStorage when `?explanation_v2=0`. `readStored()` checks `=== "1"`, so `"0"` correctly reads as false, but storing negative state is unusual for a feature flag — worth a comment.
- **[types.ts:81]** `emptyFacets` is both used as lazy init (`useState(emptyFacets)`) and called imperatively (`setFacets(emptyFacets())`). Fine either way; consider a frozen `EMPTY_FACETS` constant if reference stability ever matters.

### Recommendation

Fix **Important #1 (regenerateToken stickiness)** before commit — it silently wastes LLM spend on every navigation after the first regenerate. The rest is safe behind the feature flag; SSE error handling (#2) and SDK typing (#3) can be bundled into early Phase 4 or addressed in the same pass.

---

## Reviewer: Codex — 2026-04-13

**Files reviewed**: `frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts`, `ExplanationWorkspace.tsx`, `FacetRail.tsx`, `SourcePane.tsx`, `TranslationPanel.tsx`, plus backend stream/cache flow in `backend/services/explanation_workflow_v2.py`, `backend/services/explanation_service.py`, and the sentence-explanation endpoints in `backend/app/routers/works.py`.

**Validation**: `just lint-web` and `just typecheck` passed.

### Findings

- **Medium — reopening an in-progress explanation can restart generation instead of resuming it.**
  - `useExplanationArtifact.ts` only hydrates cached facets when `GET .../sentences/explanation` returns `status === "complete"` (`useExplanationArtifact.ts:203-217`). For `pending` / `generating`, it immediately POSTs and opens the stream.
  - On the backend, `ExplanationWorkflowV2.stream()` only replays cached facets for artifacts already marked `complete` or `error`; otherwise it drives generation again (`backend/services/explanation_workflow_v2.py:173-220`).
  - Impact: if the workspace is closed and reopened mid-run, already-persisted facet progress is not reloaded into the UI and the reopen path can trigger duplicate generation work against the same artifact.
  - Suggested fix: hydrate partial facets from `GET` for `pending` / `generating`, then open the stream without re-POSTing unless a true cache miss requires artifact creation.

- **Low — the edge-click navigation targets interfere with text selection near the pane edges.**
  - `EdgeNav` renders full-height invisible buttons over the left and right edges of the reading pane (`ExplanationWorkspace.tsx:459-488`).
  - Impact: pointer interaction in those 18px strips goes to the button, not the text, making selection/copy brittle near the edges. This conflicts with the Phase 4 requirement that edge navigation must not interfere with text selection.
  - Suggested fix: reduce the hit area, gate it to explicit affordance regions, or switch to non-overlay controls.

- **Low — the facet rail’s spinner path is currently unreachable.**
  - `FacetStatusGlyph` renders a loader for `status === "generating"` (`FacetRail.tsx:75-96`), but `useExplanationArtifact` never assigns `"generating"` to any individual facet; facet state goes from `pending` straight to `complete` / `error` (`useExplanationArtifact.ts:120-198`).
  - Impact: the rail cannot actually show which facet is in flight, even though the component suggests that it can.
  - Suggested fix: either mark the active in-flight facet as `generating` when streaming begins, or remove the dead UI state until per-facet progress exists.

---

## Review — Codex — 2026-04-13

**Files reviewed**: `frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts`, `frontend/src/components/chapterDetail/translation/explanation/ExplanationWorkspace.tsx`, `frontend/src/components/chapterDetail/translation/explanation/FacetRail.tsx`, `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`
**Changes**: Review-only pass focused on code cleanliness, structure, and simplicity

### Important
- **[frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts:89]** The regenerate path is modeled with both `regenerateToken` state and `lastProcessedTokenRef`, then decoded indirectly inside the main effect at lines 118-119. That extra lifecycle bookkeeping is what allowed the sticky-force bug to exist in the first place. Suggested fix: collapse this to a single "force once for this request key" mechanism so force semantics live with the active `(segmentId, spanStart, spanEnd, density)` tuple rather than across unrelated renders.
- **[frontend/src/components/chapterDetail/translation/explanation/ExplanationWorkspace.tsx:45]** The workspace declares a local `ChapterTranslationResponse` and reshapes it by hand at lines 90-106 even though the generated client already exposes this endpoint. That duplicates API schema in the UI layer and creates a second place that must stay aligned with backend changes. Suggested fix: consume the generated SDK/type directly and keep only the UI-specific normalization step.
- **[frontend/src/components/chapterDetail/translation/explanation/ExplanationWorkspace.tsx:65]** Segment ownership is split between the parent remounting the workspace with `key={explanationSegmentId}` in `TranslationPanel.tsx:277-285` and the child resetting `segmentId`/`sentenceIndex` in the `isOpen` effect at lines 69-75. Two reset mechanisms for the same state make the navigation model harder to reason about and easier to break later. Suggested fix: keep a single source of truth for the starting segment and remove the redundant reset path.

### Minor
- **[frontend/src/components/chapterDetail/translation/TranslationPanel.tsx:154]** `handleSegmentExplain()` still contains a `console.info` that logs segment metadata and source text. It looks like leftover instrumentation rather than product behavior and adds noise to a clean review target.
- **[frontend/src/components/chapterDetail/translation/explanation/FacetRail.tsx:75]** `FacetStatusGlyph` supports a `"generating"` branch, but no facet ever enters that state in `useExplanationArtifact.ts`. Keeping unreachable UI branches makes the rail look more complex than the actual state machine. Suggested fix: either set per-facet generating state explicitly or remove that branch until it is real.

### Summary
The delta is generally coherent, but the state/lifecycle model is still carrying avoidable complexity; I would clean up force-regeneration ownership and the duplicated API/state wiring before calling this phase structurally finished.

---


## Review — claude-opus-4-6 (cleanliness pass) — 2026-04-13

**Files reviewed**: `explanation/types.ts`, `useExplanationV2Flag.ts`, `useExplanationArtifact.ts`, `SourcePane.tsx`, `FacetRail.tsx`, `FacetContent.tsx`, `ExplanationToolbar.tsx`, `ExplanationWorkspace.tsx`, `TranslationPanel.tsx` (wiring only).

**Changes**: New two-panel Explanation Workspace (behind `?explanation_v2=1` flag) replacing the old markdown panel.

**Focus**: cleanliness / structure / simplicity — not correctness (covered by prior reviewers).

### Important

- **[ExplanationWorkspace.tsx: whole file, 613 lines]** The component does too many things: modal framing, chapter-context fetching, segment/sentence state machine, keyboard shortcuts, edge-nav overlay, toolbar, content pane, sidebar, status-label mapping, and nine local sub-components (`WorkspaceHeader`, `LoadingState`, `ErrorState`, `NotFoundState`, `SegmentBox`, `SegmentNavRow`, `SegmentFacetBody`, `FacetSidebar`, `EdgeNav`). The chapter-context loading effect (lines 77-125) is 50 lines of fetch/abort plumbing that belongs in a sibling hook (e.g. `useChapterSegments`) parallel to `useExplanationArtifact`. Split the file, otherwise every change here re-reads ~600 lines of noise.
  → Extract `useChapterSegments(workId, chapterId, isOpen)` hook; inline or consolidate the trivial state components; promote `SegmentBox` to its own file.

- **[ExplanationWorkspace.tsx:370-447]** `SegmentBox` takes 11 props, most passed straight through to `SegmentFacetBody` and `SegmentNavRow`. `canFetch`, `error`, `activeFacet`, `onFacetChange`, `facets` are threaded through `SegmentBox` only to hand to a child. Either inline `SegmentFacetBody` back into the parent (30-line conditional) or lift it out as a sibling, so `SegmentBox` owns only the reading pane.
  → Flatten the prop-drilling.

- **[ExplanationWorkspace.tsx:321-337]** `WorkspaceHeader` has zero props and is used exactly once — single-use component adding indirection without abstraction gain. Inline.

- **[ExplanationWorkspace.tsx:449-492]** `SegmentNavRow` Prev/Next duplicates the Prev/Next affordance already provided by `EdgeNav` and ArrowLeft/ArrowRight keys. Three segment-nav mechanisms on one screen — pick one or two. `SegmentNavRow` is also structurally redundant with `ExplanationToolbar` which already shows segment position.
  → Delete `SegmentNavRow` or merge segment prev/next into the toolbar.

- **[ExplanationWorkspace.tsx:130-141]** The `sentences` IIFE runs on every render to compute a trivial fallback. IIFE in JSX scope is harder to read than a named helper; the synthesize-a-whole-segment-sentence fallback is a rendering concern leaking into the workspace.
  → Extract `resolveSentences(segment)` pure helper, or push into `SourcePane`.

- **[ExplanationWorkspace.tsx:574-580]** `getStatusLabel` is a 5-line free function at the bottom of the file with one call site. Inline the four-way conditional at the call site, or move it next to `FacetRail` where it is rendered.

- **[FacetContent.tsx:52-61]** The switch uses `as` casts (`state.data as OverviewData`) because the dispatch loses the per-facet type. Since `FacetState<K extends FacetType>` already carries the key type parameter, a typed `renderers: Record<FacetType, (data) => ReactNode>` dispatch would eliminate the four casts.
  → Replace switch+cast with a typed dispatch table.

- **[FacetContent.tsx:136-171, 189-213, 215-235 + SourcePane.tsx:52-60]** `VocabCard`, `GrammarCard`, `LabeledCard`, and `Section` all repeat the same "uppercase wider bold muted label" `Text` pattern. Extract a `SectionLabel` component shared across both files.

### Minor

- **[useExplanationArtifact.ts:32-52]** `ArtifactGetResponse` is a hand-typed, three-layer nullable mirror of the backend response. Duplicates what the generated SDK should cover; if not yet covered, note it and delete later.

- **[useExplanationArtifact.ts:54-75]** `applyCachedFacets` is a single-use helper 140 lines from its call site. Consider co-locating with the GET handler.

- **[useExplanationArtifact.ts:97-102]** `cleanup` is wrapped in `useCallback` only to satisfy the exhaustive-deps lint, but it captures nothing mutable and the refs are stable. Declare as a plain function inside the effect instead — removes a self-induced dependency.

- **[useExplanationArtifact.ts:89]** `regenerateToken` + `lastProcessedTokenRef` + `isRegenerating` is three pieces of state modelling one concept ("this run was user-forced"). A single `forcedRef` set by `regenerate()` and consumed in the effect is simpler. (Overlaps with prior bug #1; a cleanup pass would fix both.)

- **[FacetRail.tsx:26]** `const Container = isHorizontal ? HStack : Stack` assigns components to a variable. Works but trips some TS/lint setups and hides which layout is used. Direct conditional render is clearer even with a bit of JSX duplication.

- **[FacetRail.tsx:75-97]** `FacetStatusGlyph` branches produce three slightly-different 6px dots plus a loader. A small `{status: {bg, isSpinner}}` table would halve the code — not worth changing unless this grows.

- **[ExplanationWorkspace.tsx:184-200]** Inline `/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)` — if this editable-target check exists elsewhere in the codebase, share it as `isEditableTarget(el)`.

- **[ExplanationWorkspace.tsx:37-53]** `ChapterSegment` (normalized internal) and `ChapterTranslationResponse` (wire shape) both live in this file. The wire shape should move next to the fetch or vanish when switching to the generated SDK.

- **[types.ts:81-88]** `emptyFacets()` allocates a fresh object per call; used as both lazy init and imperative reset. A frozen constant saves allocations. (Prior reviewer noted.)

- **[ExplanationToolbar.tsx]** Clean.

- **[SourcePane.tsx]** Clean. Local `Section` helper is appropriate single-file scope.

- **[useExplanationV2Flag.ts]** Clean. The `syncFromUrl`/`readStored` split is appropriate.

### Summary
No blocking cleanliness issues, but `ExplanationWorkspace.tsx` is overweight (613 lines, nine local sub-components, three segment-nav mechanisms, inline fetch plumbing) and should be decomposed before Phase 4 piles on more. The facet-dispatch `as` casts in `FacetContent.tsx` are the only type-safety smell worth fixing in this pass; the rest is refactor-at-leisure.

---

## Review — Codex — 2026-04-13

**Files reviewed**: `frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts`, `frontend/src/components/chapterDetail/translation/explanation/ExplanationWorkspace.tsx`, `backend/app/routers/works.py`, `backend/services/explanation_workflow_v2.py`
**Changes**: Re-review of the Phase 3 follow-up changes against prior review notes

### Important
- **[frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts:163]** The SSE error handler still reads `msg.error`, but the v2 backend emits `message` in `_v2_event_to_sse` at **[backend/app/routers/works.py:870]**. Result: facet failures and artifact-level failures lose their real backend message and collapse to the generic fallback strings in the workspace UI. → Align the event contract on one field name (`error` or `message`) and update both facet-level and artifact-level parsing together.

- **[frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts:217]** Reopening an explanation while the artifact is still `pending` / `generating` still does not resume the existing run. The hook only short-circuits on `GET .../sentences/explanation` when `status === "complete"`, then immediately POSTs again and reopens the stream; on the backend, `ExplanationWorkflowV2.stream()` only replays cached payloads for artifacts already marked `complete` or `error` at **[backend/services/explanation_workflow_v2.py:173]**. → Hydrate partial facets from the GET response and add a true "attach to in-progress artifact" path instead of re-driving generation on reopen.

### Summary
Most of the earlier review notes are addressed: the sticky force-regenerate bug is fixed, transient SSE reconnects no longer surface false errors, the workspace now uses generated chapter-translation types, the redundant reset effect and debug log are gone, and the edge-nav / facet-rail cleanup landed. Two meaningful issues remain before this follow-up can be considered fully closed: the in-progress reopen lifecycle and the frontend/backend SSE error payload mismatch.

---

## Review — Codex — 2026-04-13

**Files reviewed**: `backend/services/translation_stream.py`, `backend/services/explanation_workflow_v2.py`, `backend/services/translation_workflow.py`, `backend/app/routers/works.py`, `frontend/src/hooks/useChapterTranslationStream.ts`, `frontend/src/components/chapterDetail/translation/SegmentsList.tsx`, `frontend/src/components/chapterDetail/translation/TranslationPanel.tsx`
**Changes**: Review of the partial-translation persistence / hydration follow-up delta

### Important
- **[backend/services/explanation_workflow_v2.py:75]** The new `"partial"` segment state is not treated as untranslated before explanation generation. This delta now persists `segment.tgt` mid-stream and marks the row with `"partial"` in **[backend/services/translation_stream.py:94]**, but explanation preflight still accepts any non-empty `tgt` as translated, and the UI still enables “Explain Translation” whenever target text exists in **[frontend/src/components/chapterDetail/translation/SegmentsList.tsx:265]**. Result: users can open sentence explanations against an incomplete translation and get analysis for text that is about to change. Suggested fix: reject `"partial"` in `_is_translated()` and disable Explain unless the segment is actually complete.
- **[backend/services/translation_stream.py:240]** Manual edits do not clear the new `"partial"` flag. The existing batch edit path used by **[frontend/src/components/chapterDetail/translation/TranslationPanel.tsx:172]** updates `segment.tgt` and clears cached explanations, but leaves `flags` untouched, so an edited partial segment still satisfies `needs_translation()` and will be retransmitted on the next resume. That means a user can pause, edit the visible partial text, and then lose that edit when translation resumes. Suggested fix: treat an explicit user edit as authoritative by removing the `"partial"` flag in `batch_update_segment_translations()` and cover it with a regression test.

### Summary
The resume/hydration behavior itself looks sound and the targeted backend tests pass, but the new `"partial"` state is not integrated with existing explain/edit affordances yet. I would not treat this delta as safe to commit until those two paths are closed.

---

## Review — claude-opus-4-6 — 2026-04-13

**Files reviewed**: `backend/services/translation_workflow.py`, `backend/services/translation_stream.py`, `backend/services/explanation_workflow_v2.py`, `backend/agents/explanation_generator_v2.py`, `backend/tests/test_translation_workflow.py`, `frontend/src/hooks/useChapterTranslationStream.ts`, `frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts`
**Changes**: Post-Phase-3 hardening — partial segment-translation persistence across disconnect/resume, partial-facet replay on explanation reopen, SSE `message` field alignment.

### Important
- **[backend/services/explanation_workflow_v2.py:199, 258-263]** `any_facet_error` leaks across replay -> regeneration. If a facet was previously errored in `payload_json`, the replay loop sets `any_facet_error = True`; since errored facets are not added to `done_facets`, `generate_facets` retries them. If the retry succeeds, `update_facet` writes a `"complete"` entry, but the in-memory `any_facet_error` is still `True`, so the artifact is finalized via `mark_error("one or more facets failed")` and the final `ArtifactCompleteEvent` has `status="error"`. The persisted facets are all complete, but the artifact shows as errored — and on the next reopen the replay will fire no error events (all entries are now `"complete"`), so state is self-healing on reopen but wrong at stream close.
  → Reset `any_facet_error` to `False` before the generation loop and recompute from `generate_facets` results only, or re-derive final status from the persisted `payload_json` after the loop (single source of truth).

- **[backend/services/explanation_workflow_v2.py:198-204]** Replay emits `ArtifactErrorEvent` for facets persisted as errored, but generation immediately retries those same facets (they're not in `done_facets`). The frontend receives an error event for a facet that is about to be retried; if the user disconnects between the replay error and the successful retry, the UI is left showing a stale error for a facet that in fact succeeded server-side. The mismatch isn't a crash, but the replay/retry ordering is user-visible.
  → Either skip emitting `ArtifactErrorEvent` during replay for facets that will be retried, or mark previously-errored facets as `"pending"` in the UI contract and only emit a terminal error if the retry itself fails.

- **[backend/services/translation_workflow.py:335-338]** `persist_partial_segment_translation` commits to Postgres on *every* streamed delta. For a 2 KB segment with ~500 tokens that is ~500 UPDATE + COMMIT round trips per segment, multiplied across a chapter. This will hold a row lock and generate heavy WAL churn; it also serializes the stream behind DB fsync latency, which can perceptibly slow streaming under load. The Phase 3 goal is resumability, not per-token durability.
  → Throttle partial persistence (e.g. commit at most every N deltas or every ~250ms, and always on segment-complete/cancel). The test at `test_translation_workflow.py:309` still passes with throttling because the segment is persisted at least once before cancellation under any reasonable threshold.

- **[frontend/src/hooks/useChapterTranslationStream.ts:207]** `replaceOnNextDelta: Boolean(existing?.text)` flips on any non-empty existing text, including fully completed segments. In a scenario where `segment-start` fires for a segment whose prior state was `"completed"` (e.g. a retranslate triggered from the UI that re-emits `segment-start` for an already-finalized row), the first delta will blow away the completed text instead of appending. Today this is probably safe because `retranslateSegment` calls `updateSegmentText(segmentId, "")` first, but the invariant is implicit — any new code path that emits `segment-start` over a completed segment without clearing text will produce wrong output.
  → Gate `replaceOnNextDelta` on an explicit "partial/running" prior status rather than "any text present", or document the invariant in a code comment.

### Minor
- **[backend/services/translation_stream.py:161, 170, 182]** `persist_partial_segment_translation` and `persist_completed_segment_translation` both set `segment.explanation = None` unconditionally. For the partial path this is fine, but on the completed path it silently drops any explanation that existed before this translate call — if a user re-runs a single segment via `retranslateSegment`, their previous explanation is wiped even if the new translation is identical. The old code (`current.tgt = collected; db.commit()`) didn't touch `explanation`, so this is a behavior change piggy-backed onto the refactor.
  → Either preserve `explanation` when the new `tgt` matches the old one, or call out this semantic shift in the commit message so it isn't silent.
- **[backend/services/explanation_workflow_v2.py:185]** `except Exception: existing = ArtifactPayload()` swallows the payload-parse failure silently. The sibling `_replay_from_cache` at least logs a warning. Add a `logger.warning` here too so a corrupted payload is observable.
- **[backend/agents/explanation_generator_v2.py:153]** `skip = skip_facets or set()` treats an empty-set argument identically to `None`, which is semantically fine but relies on the `or` fallback; `skip_facets if skip_facets is not None else set()` is slightly clearer for a public-ish API.
- **[backend/tests/test_translation_workflow.py:343]** `test_resume_retranslates_partial_segment_and_clears_partial_flag` asserts `captured_contexts == [[]]`, which exercises the "partial row is excluded from context" path only incidentally (there is one segment in the chapter, so context is always empty). Consider a multi-segment variant where segment N is partial and segment N+1's context is expected to skip N.
- **[frontend/src/hooks/useChapterTranslationStream.ts:171-178]** The nested ternary for `status` is readable enough but would be clearer as a small helper (`deriveStatus(flags, tgt)`), mirroring the backend's `needs_translation`.
- **[frontend/src/components/chapterDetail/translation/explanation/useExplanationArtifact.ts:228-234]** The GET path now hydrates facets for every status including `"error"`, then falls through to POST + stream. For an artifact already marked terminal `"error"`, this re-drives generation. Behavior change vs. prior "only hydrate on complete" — probably intended (so error retries) but worth confirming.

### Summary
The partial-persistence mechanics are sound and well-tested, but the explanation-workflow retry path has a stale `any_facet_error` flag that will misreport artifact status when a previously-errored facet is retried successfully, and the per-delta DB commit in translation streaming is a real throughput concern. Recommend fixing the `any_facet_error` reset and throttling partial commits before merging; the rest are minor.

---

## Review — Codex — 2026-04-15

**Files reviewed**: `.husky/pre-commit`, `backend/services/explanation_stream.py`, `backend/services/explanation_workflow_v2.py`, `backend/services/translation_stream.py`, `frontend/src/components/chapterDetail/translation/SegmentsList.tsx`
**Changes**: Follow-up delta to block explanation on partially translated segments

### Important
- **[backend/services/translation_stream.py:240]** This patch closes the "partial rows can still be explained" path, but the companion manual-edit bug is still open. `batch_update_segment_translations()` updates `segment.tgt` and clears `segment.explanation`, yet it still leaves the `"partial"` flag intact. A user who pauses on a partial segment, edits the visible text, and later resumes translation can still have that explicit edit overwritten because `needs_translation()` will continue to treat the row as resumable machine output. Suggested fix: clear `PARTIAL_TRANSLATION_FLAG` when applying a manual edit and add a regression test through the batch edit route.

- **[.husky/pre-commit:1]** `lint-staged --no-stash` is an unrelated behavior change that removes partial-staging protection for frontend commits. With this flag, hooks run against the working tree instead of a staged snapshot, so unstaged hunks in a partially staged file can be reformatted and swept into the commit. Unless that tradeoff is explicitly intended for the whole repo, this should not ship in the same delta. Suggested fix: drop `--no-stash`, or land it separately with rationale.

### Summary
The actual issue this delta targets is valid and the fix is directionally correct: partial translations now stay blocked from explanation in both backend preflight paths and in the segment context menu. I would not mark the overall follow-up safe yet, because manual edits on partial rows are still not authoritative and the pre-commit hook change adds unrelated commit-safety risk.

---
