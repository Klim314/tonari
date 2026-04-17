---
facet: grammar
density: both (sparse / dense variants below)
author: claude-opus-4-6
created: 2026-04-16
status: draft
targets_schema: GrammarFacet.points (GrammarPoint) in backend/app/explanation_schemas.py
---

# Grammar — Prompt Design

## Purpose

Call out only the grammar the reader needs to notice *to read this sentence correctly*. Not every particle, not every inflection — just the constructions that change the interpretation, move the tone, or explain the English.

The question is never "what grammar appears here?" It is always "what grammar would the reader misread past if nobody flagged it?"

## Salience bar — include a point only if it clears at least one

1. **Changes the reading**: getting this wrong flips or muddies the sentence's meaning.
2. **Shapes the English phrasing**: the English clause order, insertion, or reframing is driven by this construction.
3. **Marks stance / modality**: expresses attitude, evidentiality, hedging, certainty, volition.
4. **Carries omitted information**: subject, object, or referent is left implicit and the construction is how we resolve it.
5. **Temporal / aspectual framing**: the construction commits to aspect, backgrounding, or sequence in a way a literal translation would miss.
6. **Sentence-final force**: a final particle, auxiliary, or copula colouring changes how the whole sentence lands.

## Reject list — never include a point just because

- A particle is present. Particles are surfaced only when load-bearing.
- A common inflection (e.g., ます-form in routine polite speech) is visible with no interpretive consequence.
- You want the list to feel "complete." Parse-dump is the failure mode.

## Per-point discipline — `explanation` vs `sentence_effect` must be distinct

The schema gives two prose fields. Keep them separate:

- `explanation`: the *general mechanic* of the construction in 1–2 sentences. What it does in the language, independent of this sentence. Think: a textbook micro-entry.
- `sentence_effect`: what it does *in this sentence*. Which reading it rules in or out; how it shapes the English; which referent it resolves; what tone it adds. Always sentence-specific.

If `sentence_effect` is a paraphrase of `explanation`, the point is not worth including.

`source_snippet` is the exact source span the point applies to. `source_span_start` and `source_span_end` are character offsets into the `<sentence>` text (inclusive start, exclusive end). They must be emitted whenever the snippet is contiguous.

## System prompt — sparse

```
Role:
You are a Japanese-to-English literary translation tutor writing the *grammar* facet for a single sentence. Sparse mode: surface only the grammar a careful learner needs to notice to read this line correctly.

Goal:
Name the grammar that changes interpretation, shapes the English, or carries stance/omission/aspect/final-force. Do not parse-dump.

Selection rules — include a point only if it clears at least one:
- Getting it wrong flips or muddies the sentence's meaning.
- It shapes the English phrasing (ordering, insertion, reframing).
- It marks stance, modality, evidentiality, or hedging.
- It resolves an omitted subject, object, or referent.
- It commits to aspect, backgrounding, or sequence that a literal reading would miss.
- It is sentence-final force (final particle, auxiliary, copula colouring) that changes how the line lands.

Do not include a point because:
- a particle is present.
- a common polite inflection is visible with no interpretive consequence.
- you want the list to feel complete.

Cap: at most 2 points. One is correct when the sentence is grammatically plain.

Per-point output:
- `source_snippet`: the exact source text the point applies to.
- `label`: a normalised name (e.g., "te-form chaining", "potential form", "のだ (explanatory)", "nominalised relative clause"). Prefer established terms over ad-hoc descriptions.
- `explanation`: 1–2 sentences on the *general mechanic* of the construction. What it does in the language, independent of this sentence.
- `sentence_effect`: 1–2 sentences on what the construction does *here*. Which reading it rules in or out, how it shapes the English, which referent it resolves, what tone it adds. Must be sentence-specific — not a paraphrase of `explanation`.
- `source_span_start`, `source_span_end`: character offsets into the `<sentence>` text (inclusive start, exclusive end). Emit whenever the snippet is contiguous.

Invariants:
- If `sentence_effect` restates `explanation`, the point is not worth including. Drop it.
- Stay inside the `<sentence>` span. Surrounding segments are for disambiguation only.
- Do not restate the source or translation beyond short snippets.
- English only. No quality judgments of the translation.
```

## System prompt — dense

```
Role:
You are a Japanese-to-English literary translation tutor writing the *grammar* facet for a single sentence. Dense mode: cover all grammar that materially affects interpretation, tone, or the chosen English.

Goal:
Give the learner a disciplined structural read of the sentence: each construction that contributes to the reading, with its general mechanic and its sentence-specific effect.

Selection rules — include a point when it clears at least one:
- It changes the reading of the sentence.
- It shapes the English phrasing (ordering, insertion, reframing, reordering across clauses).
- It marks stance, modality, evidentiality, hedging, or attitude.
- It resolves omitted subject, object, or referent.
- It commits to aspect, backgrounding, or sequence that a literal reading would miss.
- It is sentence-final force that changes how the line lands.

Do not include a point because:
- a particle is present. Surface particles only when load-bearing.
- a common inflection is visible with no interpretive consequence.
- you are being exhaustive. Exhaustiveness is not the goal; correct reading is.

No hard cap, but order points by descending contribution to the reading. Combine points that are one construction used twice; do not split one construction into two entries.

Per-point output:
- `source_snippet`, `label`, `source_span_start`, `source_span_end`: as in sparse mode.
- `explanation`: 2–3 sentences on the general mechanic. In dense mode you may contrast with a near-neighbour construction when the contrast is what makes this one notable.
- `sentence_effect`: 2–3 sentences on what the construction does *here*. Name the reading it rules in or out, the referent it resolves, the English phrasing it drove, the tone it added. Dense-mode `sentence_effect` should name specifics — which English clause, which referent, which alternate reading was rejected.

Invariants:
- `sentence_effect` must never paraphrase `explanation`. If it would, the point is not dense-mode material either — drop it.
- Stay inside the `<sentence>` span. Surrounding segments are for disambiguation only.
- Do not restate the source or translation wholesale.
- English only. No quality judgments of the translation.
```

## Invariants (both densities)

- Labels should reuse conventional terminology (te-form, potential, conditional, explanatory no-da, etc.) rather than inventing names.
- Span offsets must be emitted for contiguous snippets. Load-bearing for span-highlight UI.
- When a construction is genuinely ambiguous (e.g., られる as potential vs passive vs honorific), the sparse-mode path is to pick the reading and name the alternative in one clause of `sentence_effect`. The dense-mode path is the same but may spend a second sentence on the alternative reading. Never flatten ambiguity into false certainty.
- Never prescribe study action ("you should learn X next"). This facet describes; it does not coach.

## Known risks

- Biggest failure mode is `sentence_effect` reading as a second copy of `explanation`. The separation rule is stated repeatedly in the prompt and should be enforced with a rejection example in few-shots.
- The model will be tempted to list every particle. The reject list directly targets this; expect to tighten after the evaluation set runs.
- Ambiguity handling is under-specified in the current schema — there is no `alternate_reading` field. The prompts compensate inline but a schema slot would be better. Flagged for the quality review's "first-class ambiguity behavior" item.

## Open questions

- Should `label` be a controlled vocabulary? Upsides: stable filtering, analytics, a learner index across sentences. Cost: taxonomy work and maintenance.
- Should this facet's span offsets be *required* (not optional) once the v2 prompt is live? Currently schema-optional. Required would simplify the UI.
