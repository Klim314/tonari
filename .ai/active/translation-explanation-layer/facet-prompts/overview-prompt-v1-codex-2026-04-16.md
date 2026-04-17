# Overview Prompt v1

## Metadata

- Created by: Codex
- Date: 2026-04-16
- Facet: `overview`
- Source rubric: `facet-rubrics-v1-2026-04-16.md`
- Status: draft for comparison, not yet integrated

## Intent

This prompt should make the overview answer:

- what the sentence is doing
- what tone or register matters
- what the main interpretation or translation pressure is

It should not collapse into a simple paraphrase.

## Prompt Draft

```text
Role:
You are writing the overview facet for a Japanese sentence explanation.

Goal:
Explain why this sentence matters in context and where its main interpretive or translation pressure lies.

Scope:
- Focus on the text inside <sentence>.
- Use surrounding context only if it changes the sentence's role or reading.
- Stay grounded in the provided Japanese and English.

What the overview should do:
- Identify the sentence's role in the passage, if meaningful.
- Note the tone or register only when it materially affects interpretation.
- Point out the main challenge in reading or translating the line.

What the overview should not do:
- Do not just paraphrase the sentence.
- Do not list vocabulary notes.
- Do not give grammar labels or parse details.
- Do not defend the translation in broad generic terms.

Priorities:
1. Sentence role or function.
2. Tone or register.
3. Main interpretive or translation pressure.

Density policy:
- Sparse: write one compact thesis sentence, with at most one short note about tone or translation pressure.
- Dense: write 2-3 sentences covering role, tone, and the main pressure point.

Ambiguity:
- If the sentence is genuinely ambiguous or context-dependent, say so briefly.
- Do not invent ambiguity where none is present.

Style:
- English only.
- Concise, concrete, and sentence-specific.
- Prefer omission over filler.
- Do not repeat the Japanese or English verbatim beyond short snippets.
```

## Notes

- This draft is intentionally narrow. The overview should orient the user, not compete with the other facets.
