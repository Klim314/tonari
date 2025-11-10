from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas import ChapterDetailOut
from services.chapters import ChaptersService
from services.exceptions import ChapterNotFoundError

router = APIRouter()


@router.get("/{chapter_id}", response_model=ChapterDetailOut)
def get_chapter(chapter_id: int):
    with SessionLocal() as db:  # type: Session
        chapters_service = ChaptersService(db)
        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None
        return ChapterDetailOut.model_validate(chapter)
