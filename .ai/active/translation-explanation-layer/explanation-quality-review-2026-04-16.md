# Explanation Quality Review

## Status

- Date: 2026-04-16
- Scope: output quality and explanation-selection logic
- Non-goal: transport, storage, SSE, or concurrency mechanics

## Current Read

The v2 explanation layer has the right product shape, but the current generation logic is still too schema-first and not learner-first.

What it does well:

- It breaks explanation into useful facets instead of one markdown blob.
- It keeps analysis scoped to a sentence span.
- It already distinguishes quick vs deep output at a high level.

What is still weak:

- All four facets share the same high-level prompt, so the system is not making strong facet-specific decisions.
- `sparse` vs `dense` mostly changes volume, not selection logic.
- The output is likely to over-explain obvious content and under-explain the actual translation pressure.
- `translation_logic` is sentence-wide and blob-like, when the useful unit is usually 2-4 concrete decision points.
- There is no explicit behavior for ambiguity, uncertainty, or "multiple valid readings".
- Overview risks becoming a paraphrase instead of answering "what matters here?"

## Product Goal

The explanation should help the user answer four questions quickly:

1. What is this sentence doing here?
2. What should I notice in the Japanese?
3. Why does the English sound like this instead of a literal gloss?
4. Where is the meaning flexible, compressed, or hard to carry over?

If a facet does not help answer one of those questions, it is probably noise.

## Proposed Logic

### 1. Internal analysis pass

Before producing visible facets, the system should form a hidden sentence profile:

- scene function: narration, description, interior thought, dialogue, transition
- tone/register: plain, literary, stiff, emotional, intimate, detached
- key meaning carriers: the few words or constructions that actually drive interpretation
- translation pressure points: places where natural English pulls away from literal Japanese
- ambiguity points: places where more than one reading is genuinely plausible
- context dependency: whether surrounding lines are required to resolve ellipsis, subject, tone, or reference

This is the biggest logic gap today. Right now the system jumps directly from sentence text to facet output.

### 2. Facet selection rules

Each facet should be generated from that sentence profile with a different rubric.

#### Overview

Should answer:

- what the sentence contributes
- what the tone feels like
- what the main translation challenge is

Should avoid:

- plain content summary unless it is needed for orientation
- repeating details that belong in vocabulary or grammar

Good shape:

- one thesis sentence
- one tone note
- one "why this is not trivial to translate" note

#### Vocabulary

Only include items that clear at least one of these bars:

- materially affects meaning
- is non-literal or easy to misread
- carries tone/register/style
- is an idiom, fixed expression, or literary phrase
- is important for why the English rendering was chosen

Do not include words just because they are concrete nouns with clean dictionary meanings.

Each item should answer:

- what it means here
- what nuance it carries here
- how directly or indirectly it made it into the English

#### Grammar

Only include constructions that change interpretation, tone, or English phrasing.

Good grammar items tend to answer one of these:

- what relation is being marked?
- what stance or modality is being expressed?
- what is being omitted or left implicit?
- what temporal/aspectual framing matters?
- what sentence-final force shapes the line?

Avoid parse-dump behavior. A learner does not need every particle explained every time.

#### Translation Logic

This should be the most improved facet.

Instead of one broad block, the underlying logic should identify 2-4 decision points:

- source chunk
- literal pull
- chosen English move
- reason for the move
- what was preserved vs softened/lost

This is the facet that most directly builds trust in the translation.

### 3. Density behavior

`sparse` and `dense` should use different selection logic, not just different length targets.

`sparse`:

- overview: 1 thesis
- vocabulary: at most 3 items
- grammar: at most 2 points
- translation logic: at most 2 decisions
- bias toward the most teachable and least obvious content

`dense`:

- still prioritize, but cover all material interpretation points
- include ambiguity and alternate readings when real
- include more tone/style commentary
- allow more than one valid English framing where relevant

Dense should feel deeper, not merely longer.

## Output Improvements By Facet

### Overview

Current risk:

- "summary + tone" is too weak a contract

Better target:

- sentence role
- tone/register
- main interpretive or translation pressure

### Vocabulary

Current risk:

- dictionary entries with light sentence notes

Better target:

- fewer items
- more sentence-specific reasons
- clearer relation to the chosen English

The most valuable additions conceptually are:

- why this item matters here
- what a learner might wrongly assume
- how directly it survives in English

### Grammar

Current risk:

- isolated mini-lessons that are correct but not especially useful

Better target:

- grammar that changes the reading
- grammar that explains the English phrasing
- grammar that disambiguates subject, mood, aspect, or stance

The ideal question is not "what grammar appears?" but "what grammar does the reader need to notice to read this correctly?"

### Translation Logic

Current risk:

- high-level explanation that sounds plausible but does not expose the actual decisions

Better target:

- explicit tradeoffs
- visible movement from Japanese phrasing to English phrasing
- honest handling of ambiguity

This facet should make the user feel, "I can see why the translator made that call."

## Behavioral Rules

These matter more than schema tweaks:

- Prefer omission over obvious filler.
- Prefer sentence-specific explanation over textbook definitions.
- Mark ambiguity when it is real; do not flatten it into false certainty.
- Use surrounding context only when it changes the reading, and say so.
- Do not praise the translation in generic terms.
- Do not restate the source and target unless the restatement proves a point.
- Distinguish "literal but awkward" from "actually wrong".
- Call out tone loss or tone gain when the English had to choose.

## Highest-Leverage Changes

1. Give each facet its own explicit usefulness rubric instead of one shared generic prompt.
2. Redesign `translation_logic` around decision points rather than one sentence-wide explanation block.
3. Make `sparse` vs `dense` a selection-policy difference, not a verbosity difference.
4. Add first-class ambiguity behavior: when multiple readings are live, say so.
5. Tighten the overview so it explains the sentence's role and pressure, not just its content.

## Suggested Evaluation Set

Before changing implementation, review outputs against a small handpicked set of sentence types:

- plain narration
- literary description
- dialogue with omitted subject
- sentence-final softening or assertion
- idiomatic expression
- culturally loaded wording
- structurally ambiguous sentence
- line where English must reorder heavily

Judge each explanation on:

- usefulness in under 10 seconds
- non-obviousness
- faithfulness to the Japanese
- clarity about uncertainty
- duplication across facets
- whether it actually explains the English choice

## Recommendation

The next iteration should not start with new infrastructure. It should start with a better explanation rubric and a clearer internal decision model for what deserves explanation.

The order I would use:

1. lock the quality rubric for each facet
2. reshape translation-logic around decision points
3. define true sparse/dense selection rules
4. only then update prompts and schema where needed
