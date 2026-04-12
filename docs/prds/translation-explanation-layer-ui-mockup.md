# Translation Explanation Layer UI Mockup

## Status

- Draft
- Format: ASCII wireframe
- Companion to: [translation-explanation-layer-prd.md](/mnt/d/projects/tonari/docs/prds/translation-explanation-layer-prd.md)

## Intent

This mockup is for layout, hierarchy, and interaction discussion only.

- It does not define the final visual design.
- It assumes the current v1 scope:
  - analysis units: `segment`, `sentence`
  - densities: `sparse`, `dense`
  - facets: `overview`, `vocabulary`, `grammar`, `translation_logic`

## Evaluation Summary

The proposed interaction changes are directionally correct.

- Putting text on the left and facets on the right is the stronger desktop layout.
- Showing the whole segment while highlighting the active sentence is the right sentence-mode behavior.
- Left/right keyboard navigation is worth shipping because explanation is part of a sequential reading workflow.
- Edge-click navigation is viable, but it should be secondary to keyboard and explicit buttons.
- Source highlighting should ship, but start with span-level highlighting rather than full token-by-token interactivity everywhere.

## Why This Layout Works

### Text Left, Facets Right

Recommended.

Reasons:

- the source and translation are the primary objects of attention
- the facet rail is navigation, so it belongs in a narrower secondary column
- readers scan text first, then inspect explanation
- this makes sentence highlighting feel natural because the highlighted text stays in the main reading pane

### Whole Segment With Sentence Highlight

Recommended.

Reasons:

- segments can contain multiple sentences, so sentence analysis still needs local segment context
- users should not lose the segment boundary just because the active explanation unit is a sentence
- visually highlighting the sentence inside the larger segment pane keeps the reading surface stable

### Arrow-Key and Edge Navigation

Recommended, with constraints.

Keyboard:

- `Left Arrow`: previous segment
- `Right Arrow`: next segment

Pointer:

- clicking a narrow left-edge target moves to previous segment
- clicking a narrow right-edge target moves to next segment

Constraint:

- edge-click targets should be subtle and not interfere with text selection

### Source Token Highlighting

Recommended in a constrained form.

V1 recommendation:

- support span highlighting tied to facet cards
- support smaller token-level highlight only inside `vocabulary` cards if spans are reliable
- do not attempt full interactive tokenization across the entire reading pane in v1

Reason:

- Japanese token boundaries are useful but easy to overcomplicate
- span-level highlighting gets most of the value with much less UI and schema complexity

## Desktop Mockup: Segment Mode

```text
+====================================================================================================+
| Explanation Workspace                                                             [Close] [X]     |
+====================================================================================================+
| Unit: [Segment v]   Segment: [12 / 84]                      Density: [Sparse] [Dense] [Regenerate]|
+====================================================================================================+
| < Prev                                                                                    Next >  |
|                                                                                                    |
| SOURCE                                                                                             |
|----------------------------------------------------------------------------------------------------|
| 月の光が、古い書斎の窓から静かに差し込んでいた。                                                         |
|                                                                                                    |
| TRANSLATION                                                                                        |
|----------------------------------------------------------------------------------------------------|
| Moonlight filtered quietly through the window of the old study.                                   |
|                                                                                                    |
+==================================================================================+=================+
| MAIN TEXT / ANALYSIS                                                            | FACETS          |
|----------------------------------------------------------------------------------+-----------------|
| +------------------------------------------------------------------------------+ | > Overview      |
| | OVERVIEW                                                                     | |   Vocabulary    |
| | The translation preserves the literary softness of the original by choosing  | |   Grammar       |
| | "filtered" over a literal "shone in." The Japanese uses 差し込んでいた, an   | |   Logic         |
| | ongoing past form that implies the light is already present and continuous.   | |                 |
| | "Filtered" carries that same sense of gradual, diffuse motion in English.    | | cached · sparse |
| +------------------------------------------------------------------------------+ |                 |
+==================================================================================+=================+
```

## Desktop Mockup: Sentence Mode

In sentence mode, the pane still shows the whole segment block, but the active sentence is highlighted. In this example, segment 12 contains two sentences and sentence mode focuses the second one.

```text
+====================================================================================================+
| Explanation Workspace                                                             [Close] [X]     |
+====================================================================================================+
| Unit: [Sentence v]   Segment: [12 / 84]   Sentence: [2 / 2] Density: [Sparse] [Dense] [Regenerate]|
+====================================================================================================+
| < Prev                                                                                    Next >  |
|                                                                                                    |
| SOURCE                                                                                             |
|----------------------------------------------------------------------------------------------------|
| 月の光が、古い書斎の窓から静かに差し込んでいた。                                                       |
| [ACTIVE SENTENCE HIGHLIGHT]                                                                        |
| 埃を被った幾百もの書物が、まるで遠い昔の囁きを閉じ込めているかのようだ。                               |
| [/ACTIVE SENTENCE HIGHLIGHT]                                                                       |
|                                                                                                    |
| TRANSLATION                                                                                        |
|----------------------------------------------------------------------------------------------------|
| Moonlight filtered quietly through the window of the old study.                                   |
| [ACTIVE SENTENCE HIGHLIGHT]                                                                        |
| Dust-covered books seemed to hold within them the whispers of a distant past.                     |
| [/ACTIVE SENTENCE HIGHLIGHT]                                                                       |
|                                                                                                    |
+==================================================================================+=================+
| MAIN TEXT / ANALYSIS                                                            | FACETS          |
|----------------------------------------------------------------------------------+-----------------|
| +------------------------------------------------------------------------------+ | > Overview      |
| | OVERVIEW                                                                     | |   Vocabulary    |
| | The second sentence personifies memory and deepens the scene established      | |   Grammar       |
| | by the first sentence. Sentence mode isolates that effect for closer study.   | |   Logic         |
| +------------------------------------------------------------------------------+ |                 |
|                                                                                    | cached · sparse |
| Sentence notes:                                                                   |                 |
| - image progression: dust -> books -> whispers                                   |                 |
| - tone: archival, hushed, reflective                                             |                 |
| - why sentence mode: the segment contains multiple sentences                     |                 |
+==================================================================================+=================+
```

## Desktop Mockup: Vocabulary Facet

```text
+==================================================================================+=================+
| MAIN TEXT / ANALYSIS                                                            | FACETS          |
|----------------------------------------------------------------------------------+-----------------|
| VOCABULARY                                                                        |   Overview      |
|                                                                                    | > Vocabulary    |
| +----------------------+  +----------------------------------------+              |   Grammar       |
| | 月の光               |  | 差し込んでいた                         |              |   Logic         |
| | reading: つきのひかり |  | reading: さしこんでいた               |              |                 |
| | gloss: moonlight     |  | gloss: was shining / coming in        |              | Span links      |
| | nuance: poetic       |  | nuance: motion + softness             |              | [highlight 1]   |
| +----------------------+  +----------------------------------------+              | [highlight 2]   |
|                                                                                    |                 |
| +----------------------+                                                           |                 |
| | 書斎                 |                                                           |                 |
| | reading: しょさい     |                                                           |                 |
| | gloss: study         |                                                           |                 |
| | nuance: literary     |                                                           |                 |
| +----------------------+                                                           |                 |
+==================================================================================+=================+
```

## Desktop Mockup: Grammar Facet

```text
+==================================================================================+=================+
| MAIN TEXT / ANALYSIS                                                            | FACETS          |
|----------------------------------------------------------------------------------+-----------------|
| GRAMMAR                                                                           |   Overview      |
|                                                                                    |   Vocabulary    |
| +------------------------------------------------------------------------------+ | > Grammar       |
| | 〜ていた                                                                      | |   Logic         |
| | Effect: ongoing or scene-setting past state                                  | |                 |
| | Why it matters: the light is presented as already entering the room, not      | | Span links      |
| | as a sudden action                                                            | | [highlight 1]   |
| +------------------------------------------------------------------------------+ | [highlight 2]   |
|                                                                                    |                 |
| +------------------------------------------------------------------------------+ |                 |
| | 静かに                                                                         | |                 |
| | Type: adverb                                                                  | |                 |
| | Effect: modifies how the light enters the scene                               | |                 |
| +------------------------------------------------------------------------------+ |                 |
+==================================================================================+=================+
```

## Desktop Mockup: Translation Logic Facet

```text
+==================================================================================+=================+
| MAIN TEXT / ANALYSIS                                                            | FACETS          |
|----------------------------------------------------------------------------------+-----------------|
| TRANSLATION LOGIC                                                                 |   Overview      |
|                                                                                    |   Vocabulary    |
| +------------------------------------------------------------------------------+ |   Grammar       |
| | Literal sense                                                                | | > Logic         |
| | "The moon's light was quietly shining in through the old study's window."    | |                 |
| +------------------------------------------------------------------------------+ |                 |
|                                                                                    | Tradeoffs       |
| +------------------------------------------------------------------------------+ | - softer tone   |
| | Chosen rendering                                                             | | - more natural |
| | "Moonlight filtered quietly through the window of the old study."            | | - less literal |
| +------------------------------------------------------------------------------+ |                 |
|                                                                                    |                 |
| +------------------------------------------------------------------------------+ |                 |
| | Why this works                                                               | |                 |
| | "Filtered" preserves the softness and literary atmosphere better than a      | |                 |
| | literal "shone in."                                                          | |                 |
| +------------------------------------------------------------------------------+ |                 |
+==================================================================================+=================+
```

## Mobile Mockup

On mobile, the right rail should collapse into top tabs or a bottom sheet.

```text
+==============================================+
| Explanation                            [X]   |
+==============================================+
| Unit: [Segment v]                           |
| Segment: 12 / 84                            |
| Density: [Sparse] [Dense]                   |
+==============================================+
| Source                                        |
| 月の光が、古い書斎の窓から静かに差し込んでいた。 |
|                                              |
| Translation                                   |
| Moonlight filtered quietly through the       |
| window of the old study.                     |
+==============================================+
| Tabs                                          |
| [Overview] [Vocabulary] [Grammar] [Logic]    |
+==============================================+
| Overview                                      |
| This line sets a calm scene. "Filtered"      |
| keeps the motion soft and literary.          |
+==============================================+
| Actions                                       |
| [Prev] [Next] [Sentence Mode] [Regenerate]   |
+==============================================+
```

## Interaction Notes

### Default Open State

- open into `overview`
- use cached `sparse` if available
- if no explanation exists, generate `sparse` first

### Density Toggle Behavior

- toggling to `dense` should first check for a cached dense artifact
- if none exists, show a loading state specific to dense generation
- do not discard visible sparse content while dense is loading

### Facet Navigation

- on desktop, facets should be in a right-side rail
- on mobile, facets should collapse to tabs
- switching facets should never trigger regeneration by itself

### Segment Navigation

- keyboard navigation should work while the workspace is focused
- pointer navigation should use explicit prev/next buttons plus optional subtle edge targets
- navigation should preserve the current facet and density when moving between segments

### Source Highlighting

- clicking a vocabulary or grammar card should highlight the linked source span
- highlight spans, not every token, in the main pane
- token-level affordances are acceptable inside vocabulary cards only if span metadata is stable

## Recommended v1 UI Shape

- use a modal or large drawer, not a new standalone page
- keep the reading pane on the left and the facet rail on the right on desktop
- keep the facet set fixed to four items
- support both `segment` and `sentence` modes in the same shell
- ship span highlighting before any more ambitious token interaction

## Resolved UI Decisions

**How should sentence boundaries be detected and exposed to the UI?**

Resolved in the PRD under "Sentence Boundary Detection." The UI consumes pre-computed sentence ranges returned by the backend; it does not perform its own splitting.

**Should sentence mode auto-open when a segment contains multiple sentences?**

No. Segment mode is the default open state because the existing entry point is segment-based. If the segment contains multiple detected sentences, the UI should offer sentence mode as a focused drill-down without making it the default interpretation of the segment.

**Should edge-click navigation ship in v1 or after keyboard navigation proves sufficient?**

Edge-click navigation ships in v1 alongside keyboard navigation. Both `< Prev` and `Next >` are visible in the text pane at all times. Keyboard (`Left` / `Right`) and pointer targets are both supported from the initial release.
