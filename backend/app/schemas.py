from datetime import datetime
from string import Formatter
from typing import Any, Literal, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator

from constants.llm import AVAILABLE_MODELS, MODEL_BY_ID


class IngestSyosetuRequest(BaseModel):
    novel_id: str = Field(
        ..., pattern=r"^n[a-z0-9]+$", description="Syosetu novel identifier (e.g. n4811fg)"
    )
    chapter: int = Field(..., ge=1, description="Chapter number (1-indexed) to fetch")


class WorkImportRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="URL to the work homepage or chapter")
    force: bool = Field(default=False, description="Force re-sync even if the work exists")


class WorkOut(BaseModel):
    id: int
    title: str
    source: Optional[str] = None
    source_id: Optional[str] = None
    source_meta: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class ChapterOut(BaseModel):
    id: int
    work_id: int
    idx: int
    sort_key: float
    title: str
    is_fully_translated: bool = False

    class Config:
        from_attributes = True


class ChapterDetailOut(ChapterOut):
    normalized_text: str
    next_chapter_id: Optional[int] = None
    prev_chapter_id: Optional[int] = None

    class Config:
        from_attributes = True


class PaginatedWorksOut(BaseModel):
    items: list[WorkOut]
    total: int
    limit: int
    offset: int


class PaginatedChaptersOut(BaseModel):
    items: list[ChapterOut]
    total: int
    limit: int
    offset: int


class ChapterScrapeRequest(BaseModel):
    start: float = Field(..., ge=1, description="Starting chapter number (supports decimals)")
    end: float = Field(..., ge=1, description="Ending chapter number (supports decimals)")
    force: bool = Field(default=False, description="If true, rescrape existing chapters")

    @model_validator(mode="after")
    def validate_range(self):
        if self.end < self.start:
            raise ValueError("end must be greater than or equal to start")
        return self


class ChapterScrapeErrorItem(BaseModel):
    chapter: float
    reason: str


class ScrapeJobOut(BaseModel):
    id: int
    work_id: int
    start: float
    end: float
    status: str
    progress: int
    total: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChapterScrapeResponse(BaseModel):
    # Backward compatibility fields (optional or derived)
    work_id: int
    start: float
    end: float
    force: bool = False
    status: str
    
    # New fields
    job_id: int | None = None
    
    # These might be empty if async
    requested: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[ChapterScrapeErrorItem] = Field(default_factory=list)


class ChapterTranslationCreate(BaseModel):
    chapter_id: int
    cache_policy: str = Field(default="reuse")
    params: Optional[dict] = None


class TranslationSegmentOut(BaseModel):
    id: int
    start: int
    end: int
    order_index: int
    src: str
    tgt: str
    flags: list[str] = Field(default_factory=list)


class ChapterTranslationOut(BaseModel):
    id: int
    chapter_id: int
    status: str

    class Config:
        from_attributes = True


class ChapterTranslationStateOut(BaseModel):
    chapter_translation_id: int
    status: str
    segments: list[TranslationSegmentOut]


class ChapterPromptOverrideRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=128, description="Model identifier")
    template: str = Field(..., min_length=1, description="Prompt template to use for this run")
    parameters: Optional[dict[str, Any]] = Field(
        default=None, description="Optional structured parameter overrides"
    )


class ChapterPromptOverrideResponse(BaseModel):
    token: str
    expires_at: datetime




# Prompt-related schemas
class PromptVersionOut(BaseModel):
    id: int
    prompt_id: int
    version_number: int
    model: str
    template: str
    parameters: Optional[dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PromptOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    owner_work_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptDetailOut(PromptOut):
    """Prompt with latest version info included."""

    latest_version: Optional[PromptVersionOut] = None

    class Config:
        from_attributes = True


class PaginatedPromptsOut(BaseModel):
    items: list[PromptOut]
    total: int
    limit: int
    offset: int


class PaginatedPromptVersionsOut(BaseModel):
    items: list[PromptVersionOut]
    total: int
    limit: int
    offset: int


class PromptCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description")

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_strings(cls, v):
        """Strip whitespace from string fields"""
        if isinstance(v, str):
            return v.strip()
        return v


class PromptUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New prompt name")
    description: Optional[str] = Field(None, max_length=2000, description="New description")

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_strings(cls, v):
        """Strip whitespace from string fields"""
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """Ensure at least one field is being updated"""
        if self.name is None and self.description is None:
            raise ValueError("At least one field (name or description) must be provided")
        return self


class PromptVersionCreateRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=128, description="Model name (e.g., gpt-4)")
    template: str = Field(
        ..., min_length=1, max_length=50000, description="F-string template for the prompt"
    )
    parameters: Optional[dict[str, Any]] = Field(None, description="Optional metadata parameters")
    created_by: Optional[str] = Field(
        None, max_length=255, description="Optional creator identifier"
    )

    @field_validator("model", "template", "created_by", mode="before")
    @classmethod
    def trim_strings(cls, v):
        """Strip whitespace from string fields"""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v):
        """Ensure model is in the list of supported models"""
        if v not in MODEL_BY_ID:
            available = ", ".join(m.id for m in AVAILABLE_MODELS)
            raise ValueError(f"Invalid model '{v}'. Supported models: {available}")
        return v

    @field_validator("template")
    @classmethod
    def validate_template_syntax(cls, v):
        """Validate f-string template syntax is valid"""
        try:
            # Test that template is a valid f-string format by parsing it
            # We use a custom formatter that accepts any field names

            # This will raise ValueError if the template has invalid syntax
            list(Formatter().parse(v))
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid template syntax: {str(e)}")
        return v


class WorkPromptUpdateRequest(BaseModel):
    prompt_id: int = Field(..., description="The prompt ID to set as default for the work")


class ModelInfoOut(BaseModel):
    """Information about a supported LLM model."""

    id: str
    name: str
    provider: str
    max_tokens: int
    supports_streaming: bool = True
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0

    class Config:
        from_attributes = True


class ModelsListOut(BaseModel):
    """list of available models."""

    items: list[ModelInfoOut]
    total: int


class LabStreamRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to translate")
    model: str = Field(..., description="Model identifier")
    template: str = Field(..., description="Prompt template")
    params: Optional[dict[str, Any]] = Field(default=None, description="Optional parameters")


# Chapter Group schemas
class ChapterGroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=512, description="Group name")
    chapter_ids: list[int] = Field(..., min_items=1, description="List of chapter IDs to include")

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class ChapterGroupUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=512, description="New group name")

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class ChapterGroupMembersUpdateRequest(BaseModel):
    chapter_ids: list[int] = Field(..., description="Complete list of chapter IDs (order preserved)")


class ChapterGroupAddMembersRequest(BaseModel):
    chapter_ids: list[int] = Field(..., min_length=1, description="Chapter IDs to add to the group")


class ChapterGroupMemberOut(BaseModel):
    id: int
    chapter_id: int
    order_index: int
    chapter: ChapterOut

    class Config:
        from_attributes = True


class ChapterGroupOut(BaseModel):
    id: int
    work_id: int
    name: str
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    min_sort_key: float  # For sorting groups with chapters
    item_type: str = "group"  # Discriminator for mixed list

    class Config:
        from_attributes = True


class ChapterGroupDetailOut(ChapterGroupOut):
    members: list[ChapterGroupMemberOut]

    class Config:
        from_attributes = True


# Mixed list response (for chapters page)
class ChapterOrGroup(BaseModel):
    """Union type for mixed chapter/group list"""

    item_type: Literal["chapter", "group"]
    data: Union[ChapterOut, ChapterGroupOut]


class ChaptersWithGroupsResponse(BaseModel):
    items: list[ChapterOrGroup]  # Mixed, sorted by sort_key
    total_chapters: int
    total_groups: int
    total_items: int
    offset: int
    limit: int
