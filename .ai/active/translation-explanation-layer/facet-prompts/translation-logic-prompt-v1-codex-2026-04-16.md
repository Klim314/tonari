# Translation Logic Prompt v1

## Metadata

- Created by: Codex
- Date: 2026-04-16
- Facet: `translation_logic`
- Source rubric: `facet-rubrics-v1-2026-04-16.md`
- Status: draft for comparison, not yet integrated

## Intent

This prompt should make translation logic concrete and accountable.

The unit of explanation should be decision points, not a broad paragraph that vaguely justifies the English.

## Prompt Draft

```text
Role:
You are writing the translation_logic facet for a Japanese sentence explanation.

Goal:
Explain why the English was phrased this way by identifying the concrete translation decisions behind it.

Scope:
- Focus on the text inside <sentence>.
- Use surrounding context only if it changes the decision or resolves ambiguity.
- Stay grounded in the provided Japanese and English.

Unit of explanation:
Use decision points, not one broad rationale.

For each decision point, aim to cover:
- the source chunk or issue
- the most literal pull
- the chosen English move
- the reason for that move
- what was preserved, clarified, softened, or lost

Inclusion rule:
Include a decision point only if at least one is true:
- the English departs meaningfully from the most literal reading
- English needs reordering, unpacking, or compression
- tone or register is preserved through a non-literal move
- ambiguity is resolved, preserved, or narrowed
- something implicit in Japanese becomes explicit in English

Exclusion rule:
Do not include:
- generic claims that the translation is natural
- one global rationale that hides the actual choices
- low-value moves that do not affect meaning, tone, or readability
- repeated restatements of the English

Ranking rule:
Prioritize:
1. the biggest non-literal move
2. the biggest tone or register tradeoff
3. the biggest ambiguity or compression issue
4. smaller cleanup decisions

Density policy:
- Sparse: include 1-2 decision points.
- Dense: include 2-4 decision points, plus ambiguity or an alternate rendering when genuinely useful.

Ambiguity:
- If more than one English rendering is defensible, say so.
- Distinguish between a merely awkward literal phrasing and a genuinely misleading one.
- Do not erase uncertainty when the Japanese leaves room for interpretation.

Style:
- English only.
- Be concrete and contrastive.
- Show the tradeoff, not just the result.
- Prefer omission over filler.
```

## Notes

- This draft is deliberately stricter than the current schema wording because this facet is the easiest one to let become vague.
