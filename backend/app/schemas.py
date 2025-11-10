from typing import Any, List, Optional
from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class IngestSyosetuRequest(BaseModel):
    novel_id: str = Field(..., pattern=r"^n[a-z0-9]+$", description="Syosetu novel identifier (e.g. n4811fg)")
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
    title: str

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


class ChapterScrapeResponse(BaseModel):
    work_id: int
    start: float
    end: float
    force: bool
    status: str


class ChapterTranslationCreate(BaseModel):
    chapter_id: int
    cache_policy: str = Field(default="reuse")
    params: Optional[dict] = None


class TranslationSegmentOut(BaseModel):
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
