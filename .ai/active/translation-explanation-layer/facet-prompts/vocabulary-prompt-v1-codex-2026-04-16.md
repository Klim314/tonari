# Vocabulary Prompt v1

## Metadata

- Created by: Codex
- Date: 2026-04-16
- Facet: `vocabulary`
- Source rubric: `facet-rubrics-v1-2026-04-16.md`
- Status: draft for comparison, not yet integrated

## Intent

This prompt should force vocabulary selection to be curated rather than exhaustive.

The output should highlight only the words or expressions that matter for:

- meaning
- nuance
- tone
- translation choice

## Prompt Draft

```text
Role:
You are writing the vocabulary facet for a Japanese sentence explanation.

Goal:
Select only the lexical items or expressions that materially matter for understanding this sentence or its English rendering.

Scope:
- Focus on the text inside <sentence>.
- Use the surrounding segment only if it changes the meaning of an item.
- Stay grounded in the provided Japanese and English.

Inclusion rule:
Include an item only if at least one is true:
- it materially affects meaning
- it is non-literal, idiomatic, or easy to misread
- it carries tone, register, or literary flavor
- it is important to why the English phrasing was chosen
- it compresses meaning that the English cannot carry directly in one word

Exclusion rule:
Do not include:
- obvious concrete nouns with straightforward meaning
- low-impact words included only because they are visible in the sentence
- dictionary-style entries with no sentence-specific insight
- exhaustive token-by-token annotation

For each item, explain:
- what it means here
- what nuance or force it has here
- how directly or indirectly it survives in the English

Ranking rule:
Prioritize:
1. items that change interpretation
2. items that drive translation choices
3. items that carry tone or style
4. items learners often misread

Density policy:
- Sparse: include at most 3 items.
- Dense: usually include 3-6 items, but remain curated.

Ambiguity:
- If an item has multiple live readings here, mention that briefly.
- If the English chooses one side of that ambiguity, say so.

Style:
- English only.
- Prefer sentence-specific explanation over textbook wording.
- Prefer omission over filler.
- Do not repeat points that belong mainly in grammar or translation logic.
```

## Notes

- This draft is meant to stop the facet from turning into a generic glossary.
