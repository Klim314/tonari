from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from functools import cache
from typing import Literal

from agents.base_agent import SegmentContextInput, create_llm, render_block
from agents.furigana import get_reading
from agents.prompts import (
    FACET_GRAMMAR_DENSE,
    FACET_GRAMMAR_SPARSE,
    FACET_OVERVIEW_DENSE,
    FACET_OVERVIEW_SPARSE,
    FACET_TRANSLATION_LOGIC_DENSE,
    FACET_TRANSLATION_LOGIC_SPARSE,
    FACET_VOCABULARY_DENSE,
    FACET_VOCABULARY_SPARSE,
)
from app.config import settings
from app.explanation_schemas import (
    FACET_LABELS,
    FACET_ORDER,
    FACET_SCHEMA_MAP,
    AnyFacetData,
    FacetType,
    GrammarFacet,
    GrammarPoint,
    OverviewFacet,
    TranslationLogicFacet,
    VocabularyFacet,
    VocabularyItem,
)
from constants.llm import get_model_info

logger = logging.getLogger(__name__)

# Per-facet system prompts keyed by (facet_type, density).
_FACET_PROMPTS: dict[tuple[FacetType, str], str] = {
    ("overview", "sparse"): FACET_OVERVIEW_SPARSE,
    ("overview", "dense"): FACET_OVERVIEW_DENSE,
    ("vocabulary", "sparse"): FACET_VOCABULARY_SPARSE,
    ("vocabulary", "dense"): FACET_VOCABULARY_DENSE,
    ("grammar", "sparse"): FACET_GRAMMAR_SPARSE,
    ("grammar", "dense"): FACET_GRAMMAR_DENSE,
    ("translation_logic", "sparse"): FACET_TRANSLATION_LOGIC_SPARSE,
    ("translation_logic", "dense"): FACET_TRANSLATION_LOGIC_DENSE,
}

_HUMAN_TEMPLATE = (
    "{preceding_block}"
    "<current_segment>\n"
    "<source>\n{segment_source}\n</source>\n"
    "<sentence>\n{sentence_text}\n</sentence>\n"
    "<translation>\n{segment_translation}\n</translation>\n"
    "</current_segment>\n\n"
    "{following_block}"
    "Generate the {facet_label}."
)

# ---------------------------------------------------------------------------
# Stub data — used when no API key is configured
# ---------------------------------------------------------------------------

_STUB_DATA: dict[str, AnyFacetData] = {
    "overview": OverviewFacet(
        summary="[Stub] Placeholder explanation for the selected sentence.",
        tone="neutral",
    ),
    "vocabulary": VocabularyFacet(
        items=[
            VocabularyItem(
                surface="単語",
                reading="たんご",
                gloss="word / vocabulary item",
                part_of_speech="noun",
                nuance="Example placeholder entry.",
                translation_type="literal",
            )
        ]
    ),
    "grammar": GrammarFacet(
        points=[
            GrammarPoint(
                source_snippet="〜ている",
                label="te-iru (ongoing state)",
                explanation="Indicates a continuing action or resultant state.",
                sentence_effect="Frames the subject as being in an ongoing condition.",
            )
        ]
    ),
    "translation_logic": TranslationLogicFacet(
        literal_sense="[Stub] Literal meaning placeholder.",
        chosen_rendering="[Stub] Chosen rendering placeholder.",
        deviation_rationale=None,
        tone_tradeoff=None,
        alternate=None,
    ),
}

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class ExplanationGeneratorV2:
    """Generates structured explanation facets one at a time.

    ``generate_facets`` yields ``(facet_type, data, error)`` for each facet in
    ``FACET_ORDER``.  Each facet payload is a complete Pydantic object — no
    partial JSON is ever emitted.  When no API key is configured, stub data is
    returned so the workflow remains testable without a live LLM.
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        api_base: str | None,
        provider: str = "openai",
    ) -> None:
        self.model = model
        self.provider = provider
        self._llm = None

        if api_key:
            try:
                self._llm = create_llm(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                )
            except Exception:
                logger.warning(
                    "ExplanationGeneratorV2: failed to initialise LLM, using stub",
                    exc_info=True,
                )
        else:
            logger.info("ExplanationGeneratorV2: no API key, using stub")

        # Cache one structured-output runnable per facet type (schema only,
        # no system prompt baked in — system prompt is passed per-call).
        self._structured_llms: dict[FacetType, object] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate_facets(
        self,
        *,
        segment_source: str,
        segment_translation: str,
        span_start: int,
        span_end: int,
        density: Literal["sparse", "dense"],
        preceding_segments: list[SegmentContextInput] | None = None,
        following_segments: list[SegmentContextInput] | None = None,
        skip_facets: set[FacetType] | None = None,
    ) -> AsyncGenerator[tuple[FacetType, AnyFacetData | None, str | None], None]:
        """Yield ``(facet_type, data, error)`` for each facet in order.

        ``data`` is ``None`` and ``error`` is set when a single facet fails.
        Remaining facets continue regardless of individual errors.  Facets in
        ``skip_facets`` are not sent to the LLM and are not yielded.
        """
        sentence_text = segment_source[span_start:span_end]
        preceding_block = render_block(preceding_segments or [], "preceding")
        following_block = render_block(following_segments or [], "following")
        skip = skip_facets or set()

        for facet_type in FACET_ORDER:
            if facet_type in skip:
                continue
            system_prompt = _FACET_PROMPTS[(facet_type, density)]
            ft, data, error = await self._generate_one(
                facet_type=facet_type,
                system_prompt=system_prompt,
                segment_source=segment_source,
                segment_translation=segment_translation,
                sentence_text=sentence_text,
                preceding_block=preceding_block,
                following_block=following_block,
            )

            # Attach reliable readings via MeCab instead of LLM-generated ones
            if ft == "vocabulary" and isinstance(data, VocabularyFacet):
                for item in data.items:
                    item.reading = get_reading(item.surface)

            yield (ft, data, error)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _generate_one(
        self,
        *,
        facet_type: FacetType,
        system_prompt: str,
        segment_source: str,
        segment_translation: str,
        sentence_text: str,
        preceding_block: str,
        following_block: str,
    ) -> tuple[FacetType, AnyFacetData | None, str | None]:
        if not self._llm:
            return (facet_type, _STUB_DATA[facet_type], None)

        human_message = _HUMAN_TEMPLATE.format(
            preceding_block=preceding_block,
            segment_source=segment_source,
            sentence_text=sentence_text,
            segment_translation=segment_translation,
            following_block=following_block,
            facet_label=FACET_LABELS[facet_type],
        )

        structured_llm = self._get_structured_llm(facet_type)
        try:
            result = await structured_llm.ainvoke(
                [("system", system_prompt), ("human", human_message)]
            )
            return (facet_type, result, None)
        except Exception as exc:
            logger.exception(
                "ExplanationGeneratorV2: facet generation failed",
                extra={"facet_type": facet_type, "model": self.model},
            )
            return (facet_type, None, str(exc))

    def _get_structured_llm(self, facet_type: FacetType):
        """Return a cached ``llm.with_structured_output(schema)`` for this facet."""
        if facet_type not in self._structured_llms:
            schema = FACET_SCHEMA_MAP[facet_type]
            self._structured_llms[facet_type] = self._llm.with_structured_output(schema)
        return self._structured_llms[facet_type]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


@cache
def get_explanation_generator_v2() -> ExplanationGeneratorV2:
    model_info = get_model_info(settings.translation_model)
    provider = model_info.provider if model_info else "openai"
    api_key = settings.get_api_key_for_provider(provider)
    return ExplanationGeneratorV2(
        model=settings.translation_model,
        api_key=api_key,
        api_base=settings.translation_api_base_url,
        provider=provider,
    )


__all__ = [
    "ExplanationGeneratorV2",
    "get_explanation_generator_v2",
]
