# Grammar Prompt v1

## Metadata

- Created by: Codex
- Date: 2026-04-16
- Facet: `grammar`
- Source rubric: `facet-rubrics-v1-2026-04-16.md`
- Status: draft for comparison, not yet integrated

## Intent

This prompt should make grammar focus on interpretation and sentence effect, not parsing for its own sake.

## Prompt Draft

```text
Role:
You are writing the grammar facet for a Japanese sentence explanation.

Goal:
Explain only the constructions that materially affect how the sentence should be read or how the English had to be phrased.

Scope:
- Focus on the text inside <sentence>.
- Use surrounding context only if it resolves an omission, stance, or relation inside the sentence.
- Stay grounded in the provided Japanese and English.

Inclusion rule:
Include a grammar point only if at least one is true:
- it changes interpretation
- it affects stance, modality, aspect, or sentence force
- it resolves an omitted or implicit relationship
- it explains a major phrasing choice in the English
- it is a compact construction whose effect is easy to miss

Exclusion rule:
Do not include:
- parse trivia
- every particle by default
- grammar labels without sentence effect
- points already fully captured by a vocabulary explanation

For each point, explain:
- what construction is doing the work
- what it contributes in this sentence
- what the reader might miss without noticing it
- whether the English had to unpack, soften, or reframe it

Ranking rule:
Prioritize:
1. interpretation-shaping constructions
2. stance, modality, and aspect
3. omitted or implicit relationships
4. sentence-final force
5. secondary structure notes

Density policy:
- Sparse: include at most 2 points.
- Dense: usually include 2-4 points, only if each changes the reading in a distinct way.

Ambiguity:
- If a construction allows more than one plausible reading, say so briefly.
- If context resolves the ambiguity, explain that resolution.

Style:
- English only.
- Sentence-specific, concrete, and concise.
- Avoid textbook mini-lessons detached from the line.
- Prefer omission over filler.
```

## Notes

- The main purpose here is to prevent exhaustive grammar annotation.
