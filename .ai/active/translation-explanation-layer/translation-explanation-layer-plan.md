# Translation Explanation Layer — Implementation Plan

## Status

- Draft
- Last updated: 2026-04-12
- Companion to: [translation-explanation-layer-prd.md](translation-explanation-layer-prd.md)

## Current State

| Layer | What exists |
|---|---|
| Database | Single `explanation: Text` nullable column on `translation_segments` |
| API | GET stream + POST regenerate, both yielding SSE deltas of a markdown blob |
| Frontend | `ExplanationPanel` modal with markdown rendering and live streaming |
| Generation | `ExplanationAgent` yields unstructured text; context-aware but schema-free |

---

## Phase 1 — Schema and Backend Foundation

**Goal:** Introduce the new data model without breaking the existing feature. No visible UX change.

### Tasks

**1. New migrations**

Create `translation_explanations` and `translation_explanation_spans` tables per the PRD data model. Retain the existing `explanation` column on `translation_segments` for backward compatibility during the transition.

**2. New SQLAlchemy models**

`TranslationExplanation` and `TranslationExplanationSpan` mapped to the new tables.

**3. Sentence boundary detection**

Implement a `SentenceSplitter` protocol:

```python
class SentenceSplitter(Protocol):
    def split(self, text: str) -> list[SentenceSpan]: ...
```

Ship a greedy rule-based splitter as the default implementation. Split on `。 ？ ！ …` and multi-character sequences (`？！ ！！ …。`). Wire the splitter behind the interface so an AI-based splitter can be substituted for evaluation later without changing calling code.

**4. Extend segment GET response**

Include a `sentences` field in the segment schema:

```json
"sentences": [
  { "span_start": 0, "span_end": 22, "text": "月の光が…" },
  { "span_start": 23, "span_end": 51, "text": "埃を被った…" }
]
```

The frontend consumes pre-computed ranges and does not perform its own splitting.

### Deliverables

- Alembic migration for `translation_explanations` and `translation_explanation_spans`
- `TranslationExplanation` and `TranslationExplanationSpan` models
- `SentenceSplitter` protocol and rule-based implementation
- Updated segment response schema with `sentences`

---

## Phase 2 — Structured Generation and New API

**Goal:** New backend pipeline that generates and stores structured artifacts. Old endpoints remain functional throughout this phase.

### Tasks

**1. Structured output schema**

Define Pydantic models for each facet at both densities:

- `OverviewFacet` — summary of meaning and tone
- `VocabularyFacet` — list of `VocabularyItem` (surface, reading, gloss, part of speech, nuance, translation type)
- `GrammarFacet` — list of `GrammarPoint` (source snippet, label, plain explanation, sentence effect)
- `TranslationLogicFacet` — literal sense, chosen rendering, deviation rationale, tone tradeoff, optional alternate

Each facet item should optionally carry `source_span_start` and `source_span_end` for later highlighting.

**2. New `ExplanationGeneratorV2`**

Replaces the free-text agent. Key behaviors:

- Produces one structured JSON payload per facet
- Emits `overview` first so the UI has content while remaining facets generate
- Sparse and dense densities are separate generation presets, not display filters
- Does not stream partial JSON; each facet payload is complete before emission

**3. New `ExplanationService`**

Handles the artifact lifecycle:

- Cache lookup by `(segment_id, span_start, span_end, density)`
- Creates artifact rows and per-span rows on generation
- Stores density variants as independent `translation_explanations` rows
- Regeneration replaces only the targeted artifact; other density variants are unaffected
- Exposes `get_or_create`, `regenerate`, and `get_artifact` methods

**4. New API endpoints**

Sentence explanation (v1 primary):

```
GET  .../segments/{segment_id}/sentences/explanation
     ?span_start=&span_end=&density=
     → cached artifact with per-facet payloads, or {status: pending} on cache miss

POST .../segments/{segment_id}/sentences/explanation
     body: {span_start, span_end, density, force?}
     → {artifact_id}; idempotent if generation already in progress

GET  .../segments/{segment_id}/sentences/explanation/stream
     ?span_start=&span_end=&density=
     → SSE stream; one event per completed facet, then a completion event
```

SSE event contract:

```
explanation-facet-complete  {facet_type, payload}
explanation-complete        {artifact_id, status}
explanation-error           {facet_type?, message}
```

Every SSE event carries a complete, parseable payload. No token deltas, no partial JSON.

**5. Regenerate API client**

Run `just generate-api` once endpoints are stable and before Phase 3 frontend work begins.

### Deliverables

- Pydantic schemas for all four facets at both densities
- `ExplanationGeneratorV2` with staged generation pipeline
- `ExplanationService` with cache and lifecycle logic
- Three new endpoint handlers under `.../sentences/explanation`
- Updated frontend API client

---

## Phase 3 — Explanation Workspace UI

**Goal:** Replace the markdown modal with the two-panel workspace. Sentence mode ships here.

### Tasks

**1. `ExplanationWorkspace` component**

A large modal or drawer (not a new page). Accepts `segmentId` and optional `sentenceSpan` props. Manages artifact fetching, SSE connection, density state, facet selection, and segment navigation.

On cache hit from the GET: render all facets immediately, no SSE connection needed.
On cache miss: POST to start generation, then open the SSE stream.

**2. Left panel — source and translation pane**

Shows the full segment source text and translation. In sentence mode, the active sentence is visually highlighted within the full segment block. In segment mode, no sentence subdivision.

`< Prev` and `Next >` buttons sit in the pane header. Navigation preserves the current facet and density selection.

**3. Right rail — facet navigation**

Four items: Overview, Vocabulary, Grammar, Logic. Active item is highlighted. Switching facets never triggers regeneration. On desktop, this is a vertical rail. On mobile, it collapses to horizontal tabs above the content area.

**4. Toolbar**

```
Unit: [Sentence ▾]   Segment: 12 / 84   Sentence: 2 / 2   [Sparse] [Dense]   [Regenerate]
```

Unit selector defaults to Sentence. Density toggle checks for a cached artifact before triggering generation. If dense is not cached, show a dense-specific loading state without discarding visible sparse content.

**5. Per-facet loading states**

Each facet section renders a skeleton until its `explanation-facet-complete` event arrives. Sections do not block each other. The backend emits `overview` first so the default view has content earliest.

**6. Segment navigation**

- Keyboard: Left/Right arrow keys while workspace is focused move to previous/next segment
- Pointer: explicit `< Prev` / `Next >` buttons in the text pane header

**7. Error states**

Distinguish and render appropriately:

- No explanation generated yet
- Translation missing (cannot generate)
- Generation failed (facet-level or artifact-level)
- Stale explanation (translation changed after generation — indicator only, no auto-invalidation)

**8. Entry point**

The existing "Explain Translation" segment menu item opens the new workspace in sentence mode with the first detected sentence selected. `ExplanationPanel` (old modal) is removed once this component is live.

### Deliverables

- `ExplanationWorkspace` (shell, state, SSE lifecycle)
- `SourcePane` (source + translation + sentence highlight)
- `FacetRail` (desktop vertical rail + mobile tab variant)
- `FacetContent` (per-facet renderers for all four facets)
- `ExplanationToolbar` (unit selector, segment counter, density toggle, regenerate)
- Removal of `ExplanationPanel` and old modal wiring

---

## Phase 4 — Span Highlighting and Polish

**Goal:** Source spans feel interactive; workspace is fully navigable without a mouse.

### Tasks

**1. Span highlighting**

Clicking a vocabulary or grammar card highlights the corresponding source span in the left pane using the `source_span_start` / `source_span_end` fields from the facet payload. One active highlight at a time; deactivates on click-away.

Token-level affordances inside vocabulary cards are acceptable only if span metadata from the generator proves reliable in practice. Do not attempt full interactive tokenization across the entire reading pane.

**2. Edge-click navigation**

Subtle tap targets on the left and right edges of the text pane. Secondary to the explicit buttons and keyboard. Must not interfere with text selection.

**3. Mobile layout**

Facet rail collapses to horizontal tabs above the content area. Prev/Next and Regenerate move to a bottom action bar.

**4. Cache status badge**

Show `cached · sparse`, `cached · dense`, or `generating…` in the facet rail footer.

**5. SSE reconnect**

On connection drop: re-GET the artifact (render any completed facets), then re-open the stream for pending facets. Do not attempt to parse partial JSON from a dropped stream.

### Deliverables

- Span highlight system wired to facet card clicks
- Edge-click navigation targets
- Mobile layout (tabs + bottom bar)
- Cache status badge
- SSE reconnect logic

---

## Phase 5 — Segment Analysis Mode

**Goal:** Whole-segment explanation is available as an alternative analysis unit alongside sentence mode.

**Tasks:**

**1. Segment explanation endpoints**

```
GET  .../segments/{segment_id}/explanation?density=
POST .../segments/{segment_id}/explanation
GET  .../segments/{segment_id}/explanation/stream?density=
```

Wired to the same `ExplanationService` with `analysis_unit_type: segment` and no span rows written. Cache key is `(segment_id, density)`.

**2. Unit toggle in workspace**

The `[Sentence ▾]` selector gains a `Segment` option. Switching changes the active analysis unit and loads or triggers the segment-level artifact without closing the workspace.

**3. Cleanup**

The old `explanation` column on `translation_segments` is no longer written to by any new code path. Either remove via migration or leave as a soft-deprecated nullable field. Old streaming endpoints (`/explain/stream`, `/regenerate-explanation`) can be removed once the workspace is the sole entry point.

### Deliverables

- Three segment explanation endpoint handlers
- Unit toggle wired in `ExplanationWorkspace`
- Optional cleanup migration dropping `translation_segments.explanation`
- Removal of deprecated explanation endpoints

---

## Sequencing Notes

- **Phase 1 is a prerequisite for everything.** Pure backend, no UX risk, ships independently.
- **Phase 2 and Phase 3 are tightly coupled.** Plan to develop them together with the API stabilizing slightly ahead of the frontend. The API client regeneration step (`just generate-api`) gates the start of Phase 3 component work.
- **Old endpoints stay live** during Phase 2 and Phase 3 to avoid regressing the existing modal before the workspace is ready.
- **Phase 4 is additive polish.** Can be deferred if Phase 3 ships and is usable.
- **Phase 5 is explicitly lower priority** than shipping a good sentence-mode experience. The data model supports it from Phase 1 via `analysis_unit_type`; the implementation just has not been done yet.
