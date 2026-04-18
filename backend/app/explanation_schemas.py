from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Facet item types
# ---------------------------------------------------------------------------


class VocabularyItem(BaseModel):
    surface: str = Field(..., description="Surface form of the word or expression")
    reading: str | None = Field(None, description="Furigana / pronunciation in hiragana")
    gloss: str = Field(..., description="Plain English meaning")
    part_of_speech: str | None = Field(None, description="e.g. noun, verb, particle, expression")
    nuance: str | None = Field(None, description="Why this item is notable in this sentence")
    translation_type: Literal["literal", "adaptive", "idiomatic"] | None = Field(
        None, description="How the English translation rendered this item"
    )
    source_span_start: int | None = Field(
        None, description="Character offset within the sentence span (inclusive)"
    )
    source_span_end: int | None = Field(
        None, description="Character offset within the sentence span (exclusive)"
    )


class GrammarPoint(BaseModel):
    source_snippet: str = Field(..., description="The source text snippet this point applies to")
    highlight: str = Field(
        ...,
        description="Exact substring within source_snippet to highlight",
    )
    label: str = Field(
        ..., description="Normalized grammar label, e.g. 'te-form', 'potential form'"
    )
    explanation: str = Field(..., description="Plain English explanation of the construction")
    sentence_effect: str = Field(
        ..., description="How this construction affects the meaning of this sentence"
    )
    source_span_start: int | None = Field(
        None, description="Character offset within the sentence span (inclusive)"
    )
    source_span_end: int | None = Field(
        None, description="Character offset within the sentence span (exclusive)"
    )


# ---------------------------------------------------------------------------
# Facet types
# ---------------------------------------------------------------------------


class OverviewFacet(BaseModel):
    summary: str = Field(..., description="Concise summary of the sentence meaning")
    tone: str | None = Field(None, description="Register, mood, or stylistic note")


class VocabularyFacet(BaseModel):
    items: list[VocabularyItem] = Field(
        default_factory=list,
        description="High-value words, compounds, and expressions in this sentence",
    )


class GrammarFacet(BaseModel):
    points: list[GrammarPoint] = Field(
        default_factory=list,
        description="Notable grammar constructions and patterns in this sentence",
    )


class TranslationLogicFacet(BaseModel):
    literal_sense: str = Field(..., description="What the source literally says")
    chosen_rendering: str = Field(..., description="What the translation chose to say")
    deviation_rationale: str | None = Field(
        None, description="Why the translation deviates from the literal reading, if applicable"
    )
    tone_tradeoff: str | None = Field(
        None, description="Any tone or stylistic tradeoff in the chosen English rendering"
    )
    alternate: str | None = Field(
        None, description="An optional alternative English rendering worth noting"
    )


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

FacetType = Literal["overview", "vocabulary", "grammar", "translation_logic"]

AnyFacetData = OverviewFacet | VocabularyFacet | GrammarFacet | TranslationLogicFacet

FACET_ORDER: list[FacetType] = ["overview", "vocabulary", "grammar", "translation_logic"]

FACET_SCHEMA_MAP: dict[FacetType, type[AnyFacetData]] = {
    "overview": OverviewFacet,
    "vocabulary": VocabularyFacet,
    "grammar": GrammarFacet,
    "translation_logic": TranslationLogicFacet,
}

FACET_LABELS: dict[str, str] = {
    "overview": "overview (brief summary of meaning and tone)",
    "vocabulary": "vocabulary analysis (key words and expressions)",
    "grammar": "grammar analysis (notable constructions and patterns)",
    "translation_logic": "translation logic (how the English rendering was chosen)",
}

# ---------------------------------------------------------------------------
# Artifact payload — structure of translation_explanations.payload_json
# ---------------------------------------------------------------------------


class FacetEntry(BaseModel):
    """One facet's record as stored in and returned from the artifact payload."""

    status: Literal["pending", "generating", "complete", "error"]
    data: dict[str, Any] | None = None
    error: str | None = None


class ArtifactPayload(BaseModel):
    """Full payload stored in translation_explanations.payload_json."""

    overview: FacetEntry | None = None
    vocabulary: FacetEntry | None = None
    grammar: FacetEntry | None = None
    translation_logic: FacetEntry | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# API schemas
# ---------------------------------------------------------------------------


class ExplanationArtifactOut(BaseModel):
    """Response for GET .../sentences/explanation."""

    artifact_id: int | None = None
    status: str  # 'not_found' | 'pending' | 'generating' | 'complete' | 'error'
    density: str | None = None
    analysis_unit_type: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    facets: ArtifactPayload | None = None

    class Config:
        from_attributes = True


class ExplanationStartRequest(BaseModel):
    """Request body for POST .../sentences/explanation."""

    span_start: int = Field(..., ge=0)
    span_end: int = Field(..., gt=0)
    density: Literal["sparse", "dense"] = "sparse"
    force: bool = False


class ExplanationStartResponse(BaseModel):
    """Response for POST .../sentences/explanation."""

    artifact_id: int
