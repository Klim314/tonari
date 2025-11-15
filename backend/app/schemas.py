from datetime import datetime
from typing import Any, List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


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

    class Config:
        from_attributes = True


class ChapterDetailOut(ChapterOut):
    normalized_text: str

    class Config:
        from_attributes = True


class PaginatedWorksOut(BaseModel):
    items: List[WorkOut]
    total: int
    limit: int
    offset: int


class PaginatedChaptersOut(BaseModel):
    items: List[ChapterOut]
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


class ChapterScrapeResponse(BaseModel):
    work_id: int
    start: float
    end: float
    force: bool
    status: str
    requested: int
    created: int
    updated: int
    skipped: int
    errors: List[ChapterScrapeErrorItem] = Field(default_factory=list)


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
    flags: List[str] = Field(default_factory=list)


class ChapterTranslationOut(BaseModel):
    id: int
    chapter_id: int
    status: str

    class Config:
        from_attributes = True


class ChapterTranslationStateOut(BaseModel):
    chapter_translation_id: int
    status: str
    segments: List[TranslationSegmentOut]


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
    items: List[PromptOut]
    total: int
    limit: int
    offset: int


class PaginatedPromptVersionsOut(BaseModel):
    items: List[PromptVersionOut]
    total: int
    limit: int
    offset: int


class PromptCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Prompt name")
    description: Optional[str] = Field(None, description="Optional description")


class PromptUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="New prompt name")
    description: Optional[str] = Field(None, description="New description")


class PromptVersionCreateRequest(BaseModel):
    model: str = Field(..., min_length=1, description="Model name (e.g., gpt-4)")
    template: str = Field(..., min_length=1, description="F-string template for the prompt")
    parameters: Optional[dict[str, Any]] = Field(None, description="Optional metadata parameters")
    created_by: Optional[str] = Field(None, description="Optional creator identifier")


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
    """List of available models."""

    items: List[ModelInfoOut]
    total: int
