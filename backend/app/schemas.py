from typing import List, Optional
from pydantic import BaseModel, Field


class IngestSyosetuRequest(BaseModel):
    url: str = Field(..., description="Syosetu chapter or index URL")


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
    flags: List[str] = []


class ChapterTranslationOut(BaseModel):
    id: int
    chapter_id: int
    status: str

    class Config:
        from_attributes = True
