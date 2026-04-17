# Facet Prompt Comparison — Codex v1 vs Alternate Drafts

## Status

- Date: 2026-04-17
- Purpose: compare the current Codex-authored facet prompt drafts against the alternate prompt-design docs in the same folder
- Scope: `overview`, `vocabulary`, `grammar`, `translation_logic`

## Evaluation Categories

Use the same categories for each facet so tradeoffs are comparable:

1. **Rubric alignment** — does the prompt target the intended job of the facet?
2. **Instruction clarity** — are the selection rules and anti-failure rules explicit enough to shape behavior?
3. **Schema fit** — does the prompt tell the model how to fill the current structured fields?
4. **Boundary control** — does it avoid overlap with the other facets?
5. **Density handling** — do sparse and dense differ by selection policy rather than just length?
6. **Ambiguity / tradeoff handling** — does it tell the model how to handle uncertainty, loss, and context dependence?
7. **Ship readiness** — how close is it to a runtime prompt without another design pass?

## Cross-Prompt Read

### Where the Codex prompts are strong

- They are concise and easy to reason about.
- They inherit the rubric priorities cleanly, especially around omission over filler.
- They do a good job of defining what each facet should not become.
- `translation_logic` is pointed in the right product direction: concrete decisions, not vague justification.

### Where the Codex prompts are weak

- They are mostly rubric-shaped, not schema-shaped. They rarely tell the model how to populate the actual fields in `explanation_schemas.py`.
- Sparse vs dense is often expressed as output length rather than a materially different selection policy.
- They do not yet include strong anti-failure mechanics for the main failure modes called out in the alternate drafts.
- They under-specify span-offset behavior for `vocabulary` and `grammar`, which matters for the current Phase 4 UI work.

### Where the alternate drafts are stronger

- They are much more explicit about current schema constraints and schema mismatch.
- They define per-field responsibilities instead of only facet-level intent.
- They state invariants repeatedly, which is useful for the known failure modes.
- They are closer to runtime prompts for structured output, even when they are verbose.

### Where the alternate drafts are weaker

- They are heavier and less elegant as prompt text.
- Some sections read more like design notes than production-ready system prompts.
- The extra detail helps reliability, but it will need trimming before shipping.

## Facet Breakdown

### Overview

**Rubric alignment**

- Strength: the Codex draft captures the right three-part job: role, tone/register, and pressure.
- Strength: it clearly rejects paraphrase and broad translation-defense prose.
- Weakness: compared with the alternate draft, it gives less pressure to the "orientation first" behavior, so paraphrase remains the likely failure mode.

**Instruction clarity**

- Strength: the priority ordering is clean and easy to follow.
- Weakness: "why this sentence matters in context" is directionally right, but still broad enough to invite summary disguised as analysis.
- Weakness: the prompt does not contain a hard anti-pattern like "never begin with 'this sentence says...'", which the alternate draft wisely adds.

**Schema fit**

- Strength: it implicitly matches `OverviewFacet.summary` and `tone`.
- Weakness: it never explicitly maps role + pressure into `summary`, so the model still has to infer the field contract.
- Weakness: it does not define when `tone` should be omitted versus filled, beyond "when it materially affects interpretation."

**Boundary control**

- Strength: it avoids vocabulary, grammar, and translation-defense spillover.
- Weakness: because it does not say how to reference a pressure point without itemizing it, it may still drift into lower-level detail.

**Density handling**

- Strength: sparse vs dense is clearly shorter vs longer.
- Weakness: that is also the problem. The difference is mostly length, not selection behavior.

**Ambiguity / tradeoff handling**

- Strength: it does tell the model to mention genuine ambiguity briefly.
- Weakness: it does not explain how ambiguity should change the overview thesis itself.

**Ship readiness**

- Verdict: strong conceptual base, but not runtime-ready.
- Main gap: add field-level steering and stronger paraphrase guards before shipping.

### Vocabulary

**Rubric alignment**

- Strength: the Codex draft preserves the core salience test well: meaning, nuance, tone, and translation consequence.
- Strength: the exclusion list points in the right direction and should cut generic glossary behavior.
- Weakness: compared with the alternate draft, it does less to distinguish "interesting word" from "word that earns a schema item."

**Instruction clarity**

- Strength: the ranking rule is solid and likely to improve ordering.
- Strength: "For each item, explain..." gives the right conceptual content.
- Weakness: it never tells the model how that explanation should map into `gloss`, `nuance`, and `translation_type`.
- Weakness: it does not define what a good `surface`, `reading`, or `part_of_speech` entry looks like.

**Schema fit**

- Strength: sparse cap of 3 fits the schema's list shape well.
- Weakness: there is no mention of `translation_type` buckets (`literal`, `adaptive`, `idiomatic`), so outputs will likely be inconsistent.
- Weakness: there is no mention of `source_span_start` / `source_span_end`, despite those fields already existing and being relevant to the highlight UI.
- Weakness: without field-level guidance, dense outputs are likely to produce nice prose but weak structured data.

**Boundary control**

- Strength: it clearly tells the model not to become grammar or translation logic.
- Weakness: "it is important to why the English phrasing was chosen" is valuable, but without schema discipline it can pull the item explanations toward mini translation-logic entries.

**Density handling**

- Strength: sparse cap and dense target range are useful.
- Weakness: dense still reads as "more items" rather than a clearer salience threshold for secondary items.

**Ambiguity / tradeoff handling**

- Strength: it explicitly mentions multiple live readings and English choosing one side.
- Weakness: it does not explain where that information should live structurally, so it will probably land inconsistently inside `nuance`.

**Ship readiness**

- Verdict: good rubric prompt, weak structured-output prompt.
- Main gap: add per-field instructions and span-offset requirements before trying to ship it.

### Grammar

**Rubric alignment**

- Strength: the Codex draft keeps grammar focused on interpretation and sentence effect rather than parse trivia.
- Strength: the inclusion rule is well chosen and lines up with the rubric priorities.
- Weakness: it is still less explicit than the alternate draft about the core product distinction between "general mechanic" and "what it does here."

**Instruction clarity**

- Strength: this is the cleanest Codex draft after `translation_logic`.
- Strength: it does a good job naming the important categories: stance, modality, aspect, omission, sentence force.
- Weakness: "For each point, explain..." is weaker than explicitly binding `explanation` to the general mechanic and `sentence_effect` to the sentence-specific effect.

**Schema fit**

- Strength: the list cap and point-based structure align with `GrammarFacet.points`.
- Weakness: the prompt never names `source_snippet`, `label`, `explanation`, or `sentence_effect` explicitly.
- Weakness: it never instructs the model to emit spans, even though the schema supports them and Phase 4 wants them.
- Weakness: without explicit schema steering, the highest-risk failure is redundant prose in both `explanation` and `sentence_effect`.

**Boundary control**

- Strength: it strongly rejects vocabulary overlap and bare grammar labels.
- Weakness: it could do more to prevent particle-by-particle commentary in dense mode.

**Density handling**

- Strength: sparse cap of 2 is disciplined.
- Weakness: dense again differs mainly by count, not by a fuller rule for secondary but still load-bearing constructions.

**Ambiguity / tradeoff handling**

- Strength: it explicitly allows multiple plausible readings and context-based resolution.
- Weakness: it does not tell the model how to describe unresolved ambiguity without sounding indecisive or duplicating the overview.

**Ship readiness**

- Verdict: closest of the Codex prompts to shipping once schema-field instructions are added.
- Main gap: explicitly separate `explanation` from `sentence_effect`, and require spans for contiguous snippets.

### Translation Logic

**Rubric alignment**

- Strength: this is the strongest Codex prompt at the product level.
- Strength: it correctly defines the unit as decision points, not a sentence-wide justification blob.
- Strength: it foregrounds tradeoffs, ambiguity, and non-literal moves.

**Instruction clarity**

- Strength: the decision-point framing is concrete and high-signal.
- Strength: the ranking rule is strong and likely to surface the best content first.
- Weakness: the prompt is clear as design intent, but not clear about how that intent survives the current schema.

**Schema fit**

- Strength: none, beyond staying conceptually tied to the facet.
- Weakness: this is a direct mismatch with the current `TranslationLogicFacet`, which is blob-shaped (`literal_sense`, `chosen_rendering`, `deviation_rationale`, `tone_tradeoff`, `alternate`) rather than a list of decisions.
- Weakness: "for each decision point" cannot be expressed cleanly with today's schema, so the model would have to improvise a packing strategy.
- Weakness: compared with the alternate draft, there is no stopgap mapping from the decision-point concept into the current fields.

**Boundary control**

- Strength: it clearly distinguishes itself from generic quality praise and from repeated English restatement.
- Weakness: because the schema fit is weak, actual outputs may collapse into broad prose that overlaps with overview.

**Density handling**

- Strength: sparse vs dense is materially different here; this is the one Codex draft where density feels like selection policy, not just length.
- Weakness: that advantage is partly theoretical until the schema changes or a stopgap mapping is added.

**Ambiguity / tradeoff handling**

- Strength: strongest of all four prompts on this dimension.
- Strength: it explicitly distinguishes awkward literalness from actual misreading.
- Weakness: it does not say where tradeoff information should live in the current schema, so output consistency will be weak.

**Ship readiness**

- Verdict: best conceptual prompt, least shippable prompt.
- Main gap: either reshape the schema around decisions or write an explicit current-schema fallback first.

## Comparative Ranking

### Best by category

- **Best conceptual product direction**: `translation_logic`
- **Best current prompt discipline**: `grammar`
- **Best salience filtering instinct**: `vocabulary`
- **Biggest remaining failure mode**: `overview` drifting into paraphrase
- **Biggest schema mismatch**: `translation_logic`
- **Biggest missing runtime detail**: `vocabulary` and `grammar` span/field steering

### Best candidate to revise first

1. `vocabulary`
2. `grammar`
3. `overview`
4. `translation_logic`

Reason:

- `vocabulary` and `grammar` are structurally closest to the current schema, so field-level tightening should pay off quickly.
- `overview` needs anti-paraphrase hardening but not a schema redesign.
- `translation_logic` should not get another serious prompt pass until the team decides whether to keep or replace the current schema.

## Recommended Next Move

- Use the Codex drafts as the concise product baseline.
- Pull in the alternate drafts' schema-aware parts before any runtime integration.
- Do not treat `translation_logic` as a normal prompt-tuning problem. It is primarily a schema problem now.
- If we want one immediate prompt-revision task, start with `vocabulary` and `grammar`: add field contracts, span-offset instructions, and one or two explicit anti-failure rules each.
