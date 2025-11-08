from typing import List, Optional
from pydantic import BaseModel, Field


class IngestSyosetuRequest(BaseModel):
    novel_id: str = Field(..., pattern=r"^n[a-z0-9]+$", description="Syosetu novel identifier (e.g. n4811fg)")
    chapter: int = Field(..., ge=1, description="Chapter number (1-indexed) to fetch")


class WorkOut(BaseModel):
    id: int
    title: str

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
