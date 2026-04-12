# Translation Explanation Layer PRD

## Status

- Draft
- Last updated: 2026-04-12

## Summary

Tonari currently provides a segment-level "Explain Translation" action that streams a single markdown explanation for one translated segment. The next iteration should turn explanation into a first-class reading and study layer: structured, navigable, and useful at multiple depths.

The reference image suggests the right product direction:

- A dedicated analysis workspace instead of a plain modal
- Multiple explanation facets such as grammar, kanji, logic, and notes
- Sentence as the primary analysis unit, with the surrounding segment kept for context
- A density toggle between quick and deep analysis
- Structured cards and diagrams instead of one markdown blob

This document defines requirements for that future explanation layer. It does not prescribe the final visual style or color palette.

## Problem

The current explanation system is functional but too narrow:

- It explains one segment at a time.
- It stores explanation as a single markdown string on `translation_segments.explanation`.
- It exposes one streaming experience with no structured output contract.
- It does not distinguish explanation types such as literal meaning, grammar, translation rationale, vocabulary, or ambiguity.
- It does not support sentence-level reasoning within a segment, rare cross-segment edge cases, or learner-controlled density.
- It is better suited to "why did the model write this?" than "help me study and trust this translation."

As a result, the explanation layer is hard to scan, hard to compare across segments, and difficult to extend into more serious language-learning or editing workflows.

## Goals

- Make explanations useful for both reading comprehension and translation review.
- Support multiple explanation modes without requiring multiple separate tools.
- Replace unstructured markdown-only explanations with structured explanation data that can power richer UI.
- Allow users to move between quick summaries and deep linguistic analysis.
- Keep the explanation layer grounded in the exact source text and current translation.
- Support future reuse of explanation artifacts for caching, comparison, and analytics.

## Non-Goals

- Rebuild the entire chapter reading page in this phase.
- Match the reference image's aesthetic, theme, or layout one-to-one.
- Produce academically complete linguistic parsing for every sentence.
- Add spaced repetition, quizzes, or flashcard workflows in the first version.
- Solve full bilingual alignment at clause level across the whole chapter before shipping any improvement.

## Users

### Primary Users

- Learners reading Japanese and wanting to understand why a translation was phrased a certain way
- Advanced readers who want nuance, grammar, and lexical breakdowns
- Editors reviewing whether the translation preserved tone, logic, and implications

### Secondary Users

- Prompt engineers evaluating how model prompts affect translation decisions
- Internal developers debugging explanation quality

## Key User Jobs

- "Help me understand this sentence quickly."
- "Show me which words or grammar patterns matter most here."
- "Explain why the English translation chose this phrasing instead of a more literal one."
- "Show me where nuance, ambiguity, or loss exists."
- "Let me focus on one sentence when a segment contains multiple sentences."
- "Let me control how much explanation I get."

## Current State

### Existing Capabilities

- Segment-level explain action from the translation list
- Streaming explanation endpoint
- Regenerate explanation endpoint
- Cached explanation string persisted per translation segment
- Basic modal showing current source, current translation, and markdown explanation

### Existing Constraints

- Explanation output is a single freeform markdown field
- No structured schema for vocabulary, grammar points, logic, or notes
- No sentence analysis entity
- Minimal context window for explanation generation
- No density mode or analysis presets
- No explicit confidence, ambiguity, or "alternative rendering" fields

## Product Principles

- Structured over purely generative: the system should emit typed analysis sections wherever possible.
- Layered depth: users should get a useful result in seconds, with optional deeper inspection.
- Groundedness first: every claim should map back to visible source text and current translation.
- Reusable artifacts: generated analysis should be cacheable and independently renderable.
- Progressive disclosure: deep analysis should not overwhelm the default reading experience.

## Experience Vision

The explanation layer should feel like a study workspace attached to a translation, not a tooltip attached to a line.

Users should be able to:

- open an explanation workspace for a selected sentence within a segment
- switch between analysis facets such as summary, vocabulary, grammar, and translation logic
- inspect highlighted source spans tied to structured explanation cards
- choose between `sparse` and `dense` explanation modes
- request deeper analysis on demand without losing the base explanation

## Scope

### In Scope for the Target Design

- Sentence explanation (one detected sentence within one segment)
- Segment explanation (deferred to a later phase; schema supports it from the start)
- Structured explanation schema and storage
- Streaming and non-streaming explanation generation
- UI for multiple explanation facets
- Density presets
- Source-span highlighting and evidence mapping
- Translation rationale and alternative renderings
- Caching and invalidation rules

### Out of Scope for Initial Delivery

- Full chapter-wide explanation generation in one pass
- Teacher-authored notes
- User annotations shared across users
- Automated proficiency adaptation by JLPT level
- Audio or pronunciation coaching

## Core Concepts

### Analysis Unit

The v1 explanation layer targets `sentence` as the primary analysis unit.

- `sentence`: one detected sentence within a segment; the surrounding segment text is always included as context but the explanation is scoped to the sentence span

`segment`-level explanation (explaining the whole segment without a sentence selection) is supported by the schema and deferred to a later phase. The data model uses `analysis_unit_type` to distinguish the two, so segment analysis can be added without a schema change.

V1 constraints:
- one sentence per explanation artifact
- the sentence is always fully contained within one segment
- cross-segment sentence spans are out of scope

Rationale:
- the current segment boundary is a layout and translation unit, not a sentence boundary
- sentence-level analysis is more precise and more useful for study than explaining an arbitrarily-bounded segment slice
- scoping to one sentence keeps generation focused and reduces hallucination risk from over-broad context

### Explanation Density

The system should support at least two user-selectable densities:

- `sparse`: short, high-signal analysis for fast reading
- `dense`: fuller linguistic and translation commentary

Density changes should affect both generation depth and UI presentation.

Density must be treated as a generated artifact variant, not just a display toggle:

- `sparse` and `dense` results should be stored separately
- toggling density should first fetch the stored result for that density if it exists
- generation should only run on a cache miss or explicit regenerate
- regenerating one density does not affect the other

### Explanation Facets

V1 explanation should support exactly four typed sections:

- `overview`: quick summary of meaning and tone
- `vocabulary`: important words, compounds, expressions, and notable kanji terms
- `grammar`: constructions, particles, conjugations, and sentence patterns
- `translation_logic`: why the English phrasing was chosen

Deferred facets for later consideration:

- `structure`
- `ambiguities`
- `notes`

Kanji-specific explanation should be folded into `vocabulary` for now rather than exposed as its own facet.

## Functional Requirements

### 1. Entry Points

- The primary entry point is sentence selection: the user selects or activates a detected sentence within a segment.
- The existing segment-level "Explain Translation" action should route to sentence mode, using the first detected sentence if no selection is active, or prompting sentence selection.
- The system should allow opening explanation in an overlay first, with a path to a dedicated workspace later.

### 2. Explanation Workspace

- The explanation UI must show the active source text and current translation prominently.
- On desktop, the main text pane should sit on the left and the facet rail should sit on the right.
- In `sentence` mode, the full surrounding segment content should remain visible, with the active sentence visually highlighted.
- The UI must support switching between explanation facets without regenerating the entire payload.
- The UI must render both compact and deep views from the same underlying analysis object where possible.
- The UI must preserve reading context when switching between segments.
- The UI must make it obvious whether content is cached, streaming, or regenerated.
- Left and right arrow keys should move to the previous or next segment.
- Clicking the left or right edge of the text pane should also move to the previous or next segment.

### 3. Structured Output

- The explanation generator must return structured JSON, not only markdown text.
- Each facet should have a typed payload contract.
- Freeform markdown may still exist as a fallback or notes field, but not as the primary contract.
- Each explanation item should optionally include source span references.
- Each explanation item should optionally include translation span references when relevant.

### 4. Vocabulary / Kanji Breakdown

- The system should identify high-value lexical items rather than every token by default.
- For each selected item, the system should support:
  - surface form
  - reading
  - gloss
  - part of speech or lexical category where meaningful
  - why the item matters in this sentence
  - whether the chosen English translation is literal, adaptive, or idiomatic
- Kanji-specific detail should live inside the vocabulary facet for v1, including when relevant:
  - term
  - reading
  - plain-English meaning
  - sentence-specific nuance
  - optional note on literary, archaic, or stylistic usage

### 5. Grammar Breakdown

- The system should identify the most instructionally relevant grammar points.
- Each grammar point should include:
  - source snippet
  - normalized grammar label
  - plain explanation
  - sentence-specific effect
  - optional contrast with a nearby alternative interpretation
- Grammar output should prefer usefulness over exhaustive parse dumps.

### 6. Translation Logic

- The system should explain why the English translation was phrased the way it was.
- It should call out:
  - literal meaning
  - chosen rendering
  - reason for deviation from literal wording
  - tone or stylistic tradeoff
  - optional alternate translation
- The system should explicitly flag when a rendering is uncertain or one of multiple valid options.

### 7. Sentence Analysis

Sentence analysis is the primary v1 explanation mode.

- Each explanation artifact targets one detected sentence within a segment.
- The surrounding segment text is always passed as context but the explanation is scoped to the sentence span.
- Sentence analysis must cover:
  - the full clause-level meaning of the selected sentence
  - referent resolution where needed
  - the most relevant vocabulary and grammar inside that sentence span
  - why the English translation for that sentence was phrased the way it was
- If a sentence truly spans multiple translation segments, the schema may support multiple span rows later, but that is out of scope for v1.

### 8. Density Modes

- `sparse` mode should prioritize quick comprehension:
  - overview
  - 1-3 key vocabulary items
  - 1-2 important grammar points
  - short translation rationale
- `dense` mode should add:
  - more lexical detail
  - broader discourse notes
  - more detailed translation tradeoff commentary

Both density variants should be persisted independently so the user can toggle between them without paying generation cost every time.

### 9. Regeneration and Invalidation

- Users must be able to regenerate explanation for the current unit.
- Explanation artifacts are not automatically invalidated when the translation changes. They are records of the machine translation state at the time of generation.
- Regeneration is the only mechanism that replaces an artifact.
- The system should support regenerating one facet without necessarily discarding the whole explanation object in later phases.

### 10. Loading and Streaming

- On cache hit, the UI renders all facets immediately from the GET response; no SSE connection is needed.
- On cache miss, the UI opens an SSE stream after the POST and renders each facet as its `explanation-facet-complete` event arrives.
- Each facet section shows a loading state until its event arrives; sections do not block each other.
- The backend emits `overview` first so the default view has content while the remaining facets generate.
- If the SSE connection drops, the client recovers by re-GETting the artifact (rendering any completed facets) and re-opening the stream for the remainder.
- The UI must not attempt to parse partial JSON; every SSE event carries a complete payload.

### 11. Error Handling

- The UI must distinguish:
  - no explanation generated yet
  - explanation unavailable because translation is missing
  - generation failed
  - explanation was generated against an earlier translation (optional staleness indicator)
- Partial facet failure should not block display of successful facets when possible.

## UX Requirements

### Information Architecture

The explanation workspace should have three persistent anchors:

- source and translation focus area
- facet navigation
- analysis content area

Optional secondary controls:

- density toggle
- regenerate action
- context analysis action

### Interaction Model

- Clicking or right-clicking a segment should still support explanation entry, opening the workspace with the first detected sentence selected.
- The selected source text should remain visible while the user explores explanation facets.
- Highlighting a card or explanation item should highlight the corresponding source span when available.
- Source highlighting should ship at span level first, not full token-by-token interactivity across the entire sentence.
- Token-level highlighting can appear inside the `vocabulary` facet if the payload includes reliable spans.
- Switching density should be fast and predictable; if regeneration is required, the UI must say so.

### Content Presentation

- Use cards, sections, labels, and chips for scannability.
- Do not render the primary experience as an undifferentiated markdown article.
- Make the English translation rationale visually distinct from vocabulary or grammar notes.
- Preserve whitespace and source formatting for Japanese text.

## Data Model Requirements

The current `translation_segments.explanation` text column is insufficient for the target design.

### Span Coordinate System

All source span references use **segment-relative coordinates**: character offsets within the text of a specific `translation_segments` row.

Rationale:

- The existing model is already segment-anchored. Segment-relative spans extend naturally without introducing a parallel coordinate system.
- Character offsets remain small (typically two or three digits) because segments are short.
- Chapter-relative coordinates would require persisting or computing each segment's offset within the full chapter text, which is fragile under re-import or re-segmentation.

Most sentence explanations reference one `(segment_id, start, end)` tuple inside the selected segment. The span table may support multiple tuples later for rare cases where one sentence must be represented across segment boundaries. See `translation_explanation_spans` below.

### Recommended New Persistence Shape

Introduce a dedicated explanation artifact model instead of overloading the segment row:

- `translation_explanations`
  - id
  - analysis_unit_type (`segment`, `sentence`)
  - anchor_segment_id — the segment containing the explained unit; for sentence analysis this is always the segment the sentence belongs to, since a sentence is a subsection of a single segment
  - chapter_translation_id
  - density
  - status
  - schema_version
  - payload_json
  - generator_version
  - created_at
  - updated_at
  - invalidated_at nullable

- `translation_explanation_spans`
  - explanation_id FK → translation_explanations
  - segment_id FK → translation_segments
  - span_start — character offset within segment source text (inclusive)
  - span_end — character offset within segment source text (exclusive)
  - position — ordering when multiple rows exist for a multi-span sentence explanation

Sentence explanations normally write one span row for the selected sentence inside the current segment. If later we need to support a sentence across multiple segments, one row can be written per contributing segment. Segment-level explanations (whole segment, no sub-selection) may omit span rows entirely, which is interpreted as covering the full segment text.

Optional later table:

- `translation_explanation_facets`
  - explanation_id
  - facet_type
  - status
  - payload_json

### Cache Key Composition

Cache keys identify a unique explanation artifact. They do not encode source content — invalidation is explicit, not hash-driven.

**Segment explanation:**

```
(segment_id, density)
```

**Sentence explanation:**

```
(segment_id, span_start, span_end, density)
```

`generator_version` is treated as a fixed constant for now. If the generator changes, artifacts are refreshed by manual regeneration rather than automatic invalidation.

### Data Rules

- Explanation artifacts are records of a machine-generated translation moment. If a human edits the translation after an explanation is generated, the explanation is left in place as a record of the original translation state.
- The only mechanism that replaces an explanation artifact is explicit user-initiated regeneration.
- Density variants must be stored as independent artifacts, each with their own `translation_explanations` row.
- Existing plain markdown explanation may remain temporarily for backward compatibility during migration.
- Optional: the artifact may store a snapshot hash of the translation text at generation time so the GET response can surface a staleness indicator when the current translation has diverged. This does not trigger invalidation.

## API Requirements

### New or Revised API Shape

Recommended API capabilities:

**Sentence explanation (v1 primary)**

- `GET /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/sentences/explanation`
  - query params: `span_start`, `span_end`, `density`
  - returns the cached artifact if present; each facet carries its own status so the client can render completed facets immediately and knows which are still pending
  - on cache miss, returns a minimal artifact with `status: pending` and no facet payloads
- `POST /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/sentences/explanation`
  - kicks off generation for the sentence span and requested density; returns immediately with the artifact id
  - if generation is already in progress for the same cache key, returns the existing artifact id
- `GET /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/sentences/explanation/stream`
  - query params: `span_start`, `span_end`, `density`
  - opens an SSE connection that emits one event per completed facet, then a final completion event
  - the client opens this after the POST; if the connection drops, reconnect and re-GET the artifact to recover completed facets, then re-open the stream for any remaining

**Segment explanation (Phase 3)**

- `GET /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/explanation`
- `POST /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/explanation`
- `GET /works/{work_id}/chapters/{chapter_id}/segments/{segment_id}/explanation/stream`

### Request Parameters

- `density`
- `force`
- `span_start` and `span_end` — character offsets identifying the sentence within the segment; required for sentence endpoints, supplied as query params on GET/stream and body params on POST

The server determines which facets to generate. Clients do not specify `facet_types`. This leaves room for the server to generate additional or optional facets in future versions without requiring a client-side contract change.

### Response Requirements

- Stable explanation artifact id
- artifact-level status (`pending`, `generating`, `complete`, `error`)
- per-facet status and payload; facets with `status: complete` include their full structured payload
- metadata: cache freshness, schema version, density

### SSE Event Contract

Each SSE event carries a complete, parseable payload — no token deltas, no partial JSON.

Event types:

- `explanation-facet-complete` — emitted once per facet as it finishes; carries `facet_type` and the full facet payload
- `explanation-complete` — emitted when all facets have finished or exhausted; carries the final artifact status
- `explanation-error` — carries `facet_type` if the failure is facet-scoped, or no facet type if generation could not start; a facet-level error does not prevent other facets from completing

The backend should emit `overview` first since it is the default open facet.

On a cache hit the GET returns the full artifact immediately and no SSE connection is needed.

## Generation Requirements

### Prompt / Model Behavior

- The generator should be told to produce structured outputs aligned to the explanation schema.
- It should be instructed to stay grounded in the visible source and current translation only.
- It should distinguish observed facts from interpretation.
- It should prefer high-value language points over exhaustive low-value enumeration.
- It should explicitly mark uncertainty rather than invent certainty.
- V1 generation should only target the four supported facets.

### Multi-Step Generation

The likely implementation should be staged rather than one monolithic generation:

- Stage 1: identify unit boundaries and high-value spans
- Stage 2: generate facet payloads
- Stage 3: optionally synthesize an overview summary

For sentence analysis, the same pipeline should work over a caller-provided sentence span derived from the selected segment text.

This makes quality control, caching, and retry behavior more manageable.

### Quality Guardrails

- Do not claim grammar points unsupported by the source text.
- Do not explain kanji entries that are not actually present in the active source span.
- Do not present alternative translations as superior unless justified.
- Prefer omission over hallucinated detail.

## Performance Requirements

- Cached explanation fetch should feel effectively immediate.
- Sparse explanation generation should be optimized as the default path.
- Dense explanation generation may take longer; individual facets should still become available as they complete.
- The system should avoid regenerating unchanged facets.

## Deferred Considerations

### Analytics

Analytics are explicitly deferred for now.

Rationale:

- this is currently a single-user project
- instrumentation would add implementation overhead without changing the immediate product direction
- the explanation system should first stabilize at the schema, UX, and generation layers

If the project expands to multi-user usage later, revisit:

- explanation open rate
- regeneration rate
- density mode selection
- facet usage by type
- sentence analysis usage
- latency to first visible analysis
- explanation helpfulness feedback

## Rollout Plan

### Phase 1: Structured Sentence Explanation

- Replace markdown-only payloads with a structured schema
- Sentence is the primary analysis unit; segment analysis is deferred
- Support `overview`, `vocabulary`, `grammar`, and `translation_logic`
- Ship `sparse` and `dense` density modes
- Ship sentence boundary detection backend interface
- Entry point: sentence selection within a segment

### Phase 2: Richer UI and Span Highlighting

- Add facet navigation rail
- Add source-span highlighting tied to facet cards
- Improve caching and partial regeneration

### Phase 3: Segment Analysis

- Add segment-level explanation as an alternative analysis unit
- Entry point: existing segment-level action without sentence selection

## Risks

- Structured LLM output may be brittle if the schema is too ambitious on day one.
- Streaming partial JSON can complicate client logic.
- Segment boundaries may be too coarse for grammar explanation in some cases.
- Dense mode may become verbose without strong prompt discipline.
- Sentence boundary detection may be brittle if chapter text is noisy or irregularly segmented.

## Dependencies

- Backend schema changes and migration plan
- New explanation generation contract and prompt updates
- Frontend explanation workspace redesign
- API client regeneration once endpoints settle

## Sentence Boundary Detection

Sentence boundaries are computed on the backend and returned alongside the segment payload. The UI consumes pre-computed sentence ranges and does not perform its own splitting.

The default implementation uses a greedy rule-based splitter. Split on common Japanese sentence terminators: `。` `？` `！` `…` and multi-character sequences such as `？！` `！！` `…。`. The splitter must be implemented behind an interface so an AI-based splitter can be substituted later for evaluation or production use without changing the calling code.

## Open Questions

None currently open.

### Resolved

- **Do we want explanations tied to manual edits separately from machine-generated translations?** No. Explanations are records of the machine translation state at the time of generation. If a human edits the translation, the explanation is left in place. Regeneration is always explicit.
- **Should alternative translations be generated by the explanation system or reused from retranslation logic?** Generated by the explanation system. Alternative translations in the explanation context are illustrative renderings that support understanding of the translation choice, not viable translation candidates. Coupling to retranslation logic would be an unnecessary dependency.
- **Should explanation quality feedback be part of v1 or added after the structured pipeline is stable?** Deferred. Analytics are already explicitly deferred for a single-user project. Collecting feedback before generation quality and schema stabilize has no payoff.

## Recommended First Implementation Decisions

- Start with sentence analysis; defer segment analysis to Phase 3.
- Ship four facets first: `overview`, `vocabulary`, `grammar`, `translation_logic`.
- Implement `sparse` and `dense` as explicit backend generation presets.
- Persist each density as its own generated artifact variant.
- Persist explanation payloads in a dedicated JSON-backed table rather than the existing text column.
- Keep markdown only as an internal fallback, not the primary UI contract.
- Ship sentence boundary detection behind an interface so the splitter can be swapped later.

## Acceptance Criteria for the First Milestone

- A detected sentence within a segment can return a structured explanation artifact with at least four facets.
- The frontend can render sparse and dense views without relying on markdown parsing for the main experience.
- Regenerating explanation creates or refreshes a structured artifact for the selected sentence.
- Users can understand the meaning, major grammar, and translation rationale of a sentence in one place.
- The surrounding segment text is visible in the workspace while a sentence explanation is active.
