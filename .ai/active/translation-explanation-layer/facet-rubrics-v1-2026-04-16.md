# Facet Rubrics v1

## Status

- Date: 2026-04-16
- Purpose: first concrete rubric set for the current four explanation facets
- Use: product/design artifact to compare against later rubric drafts before prompt changes

## How To Use This Document

This document defines what a good output for each current facet should do.

It is not yet a prompt.

It should be used to:

- compare rubric variants against each other
- decide what each facet is responsible for
- reduce overlap between facets
- give the prompt pass a stable target

## Global Rules

These rules apply to all facets:

- Stay grounded in the selected sentence span first; use surrounding context only when it changes the reading.
- Prefer omission over obvious filler.
- Prioritize sentence-specific explanation over textbook description.
- Do not praise the translation in generic terms.
- Do not paraphrase the whole sentence unless that paraphrase proves a point.
- Flag genuine ambiguity instead of flattening it.
- Avoid repeating the same point across multiple facets unless each facet adds a clearly different angle.

## Cross-Facet Boundaries

Use these boundaries to reduce duplication:

- `overview` explains sentence role, tone, and where the difficulty lives.
- `vocabulary` explains high-value lexical choices and phrase-level expressions.
- `grammar` explains constructions that change interpretation or English phrasing.
- `translation_logic` explains the concrete decisions made in moving from Japanese to English.

If a point can fit multiple facets, use this tiebreak:

- If it is primarily about word meaning or phrase nuance, put it in `vocabulary`.
- If it is primarily about structure, stance, omission, aspect, or sentence force, put it in `grammar`.
- If it is primarily about why the English was phrased a certain way, put it in `translation_logic`.
- If it is primarily about what matters overall, put it in `overview`.

## Overview Rubric

### Job

Tell the user why this sentence matters and what kind of reading problem it presents.

### Primary question

What is this sentence doing, and what is the main thing the reader should understand about how it works?

### Include

- the sentence's role in the passage
- the tone or register if it materially affects interpretation
- the main translation or interpretation pressure
- a brief note on context dependence when relevant

### Exclude

- plain summary when the role can be described more usefully
- word-level mini explanations
- grammar labels or detailed parsing
- broad translation-defense prose

### Ranking rule

Prioritize:

1. sentence function
2. tone/register
3. main difficulty or pressure point

If one of these is not meaningful for the sentence, omit it.

### Output target

- `sparse`: 1 compact thesis, optionally with one tone or pressure note
- `dense`: 2-3 sentences covering role, tone, and the main interpretive or translation challenge

### Success test

The user should be able to read the overview first and know:

- why the sentence matters
- whether the line is straightforward or delicate
- where to pay attention in the deeper facets

### Failure patterns

- content summary disguised as analysis
- repeating vocabulary or grammar details that belong elsewhere
- vague claims like "this is poetic" without saying how that matters

## Vocabulary Rubric

### Job

Surface the few lexical items or expressions that actually matter for understanding the sentence or the English rendering.

### Primary question

Which words or phrases does the reader need to notice because they carry meaning, nuance, tone, or translation consequences?

### Include only if at least one is true

- it materially affects meaning
- it is non-literal, idiomatic, or easy to misread
- it carries register, tone, or literary flavor
- it is important to why the English phrasing was chosen
- it compresses more meaning than the English can carry directly

### Exclude

- obvious concrete nouns with straightforward dictionary meaning
- items included only because they are visually salient
- items whose explanation adds no sentence-specific insight
- long lists of low-impact terms

### What each item should answer

- what it means here
- what nuance or force it has here
- whether the English keeps it directly, adapts it, or drops part of it

### Ranking rule

Prioritize in this order:

1. items that change interpretation
2. items that drive translation choices
3. items that carry tone/style
4. items that are teachable because learners often misread them

### Output target

- `sparse`: at most 3 items
- `dense`: usually 3-6 items, but still curated rather than exhaustive

### Success test

The user should come away feeling:

- "I know which words actually matter here"
- "I see why these words are not just dictionary lookups"
- "I understand how these choices shaped the English"

### Failure patterns

- vocabulary list as annotation dump
- generic glosses with no sentence-specific reason
- duplicating translation-logic instead of explaining the lexical basis for it

## Grammar Rubric

### Job

Explain the constructions that materially affect how the sentence should be read or how the English had to be phrased.

### Primary question

What structural features of the Japanese does the reader need to notice to interpret this sentence correctly?

### Include only if at least one is true

- it changes interpretation
- it affects stance, modality, aspect, or sentence force
- it resolves an omission or relationship that English must make more explicit
- it explains a major phrasing choice in the translation
- it is a compact construction whose effect is easy to miss

### Exclude

- parse trivia
- every particle by default
- isolated grammar notes with no sentence-level effect
- constructions whose explanation is already fully captured by a vocabulary item

### What each point should answer

- what construction is doing the work
- what it contributes in this sentence
- what the reader might miss without noticing it
- whether English had to unpack, soften, or reframe it

### Ranking rule

Prioritize in this order:

1. interpretation-shaping constructions
2. stance/modality/aspect
3. omitted or implicit relationships
4. sentence-final force
5. secondary structure notes

### Output target

- `sparse`: at most 2 points
- `dense`: usually 2-4 points, only if each changes the reading in a distinct way

### Success test

The user should feel:

- "I see what structure I needed to notice"
- "I understand how the Japanese reading differs from a naive word-by-word read"
- "I see why the English could not mirror the Japanese structure exactly"

### Failure patterns

- mini textbook detached from the sentence
- explaining everything equally
- re-labeling the sentence without clarifying its effect

## Translation Logic Rubric

### Job

Make the translation feel accountable by showing the concrete decisions behind the English wording.

### Primary question

Why does the English say it this way instead of following the Japanese more literally?

### Unit of explanation

Use decision points, not a broad paragraph.

Each decision point should ideally cover:

- source chunk or issue
- literal pull
- chosen English move
- reason for the move
- what was preserved, softened, clarified, or lost

### Include only if at least one is true

- the English departs meaningfully from the most literal reading
- English needs reordering, unpacking, or compression
- tone/register is preserved through a non-literal move
- ambiguity is resolved, preserved, or narrowed
- something important is implicit in Japanese but explicit in English

### Exclude

- generic statements that the translation is "natural"
- restating the sentence in English twice
- one global rationale that hides the actual decisions
- low-value decisions that do not change meaning, tone, or readability

### Ranking rule

Prioritize in this order:

1. the biggest non-literal move
2. the biggest tone/register tradeoff
3. the biggest ambiguity or compression issue
4. smaller cleanup decisions

### Output target

- `sparse`: 1-2 decision points
- `dense`: 2-4 decision points, plus ambiguity or alternate rendering when genuinely useful

### Success test

The user should feel:

- "I can see what the translator had to choose"
- "I understand the tradeoff, not just the result"
- "I know whether another rendering was possible"

### Failure patterns

- explanation that sounds persuasive but names no specific decisions
- describing the chosen English without contrasting it with the literal pull
- hiding ambiguity where it actually matters

## Density Policy

Density should change selection, not just length.

### Sparse

Goal:

- fast orientation
- minimum useful set
- highest-signal points only

Policy:

- include only what changes understanding or trust
- skip anything that is technically correct but low-value
- optimize for a user who wants the explanation in under 10 seconds

### Dense

Goal:

- fuller understanding
- expose secondary but still meaningful nuance
- make uncertainty and alternatives visible

Policy:

- include all material interpretation points
- allow ambiguity and alternate renderings when real
- still avoid exhaustive annotation

## Comparison Notes

When comparing this rubric draft against future variants, judge them on:

- clarity of facet boundaries
- resistance to filler
- ability to produce non-overlapping outputs
- usefulness for both sparse and dense modes
- how well `translation_logic` becomes concrete instead of vague

## Recommendation

Use this as the baseline rubric set for the first prompt rewrite attempt.

If the first prompt pass still produces overlap or filler, the next likely refinement is not more wording. It is tightening the inclusion rules even further, especially for `vocabulary` and `translation_logic`.
