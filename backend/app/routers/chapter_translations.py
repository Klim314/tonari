from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Chapter, ChapterTranslation, TranslationSegment
from app.schemas import (
    ChapterTranslationCreate,
    ChapterTranslationOut,
    TranslationSegmentOut,
)
from app.translation_service import segment_and_translate


router = APIRouter()


@router.post("/", response_model=ChapterTranslationOut)
def create_chapter_translation(payload: ChapterTranslationCreate):
    with SessionLocal() as db:  # type: Session
        chapter = db.get(Chapter, payload.chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")

        ct = ChapterTranslation(
            chapter_id=chapter.id,
            status="running",
            cache_policy=payload.cache_policy,
            params=payload.params or {},
        )
        db.add(ct)
        db.flush()

        # Prototype: synchronous segmentation+translation
        spans = segment_and_translate(chapter.normalized_text)
        segments: list[TranslationSegment] = []
        for i, seg in enumerate(spans):
            start, end = int(seg["start"]), int(seg["end"])
            ts = TranslationSegment(
                chapter_translation_id=ct.id,
                start=start,
                end=end,
                order_index=i,
                tgt=seg["tgt"],
                flags=seg.get("flags", []),
                cache_key=None,
                src_hash="",
            )
            segments.append(ts)
        db.add_all(segments)
        ct.status = "completed"
        db.commit()
        db.refresh(ct)
        return ChapterTranslationOut.model_validate(ct)


@router.get("/{ct_id}", response_model=ChapterTranslationOut)
def get_chapter_translation(ct_id: int):
    with SessionLocal() as db:  # type: Session
        ct = db.get(ChapterTranslation, ct_id)
        if not ct:
            raise HTTPException(status_code=404, detail="not found")
        return ChapterTranslationOut.model_validate(ct)


@router.get("/{ct_id}/segments", response_model=list[TranslationSegmentOut])
def list_translation_segments(ct_id: int):
    with SessionLocal() as db:  # type: Session
        ct = db.get(ChapterTranslation, ct_id)
        if not ct:
            raise HTTPException(status_code=404, detail="not found")
        chapter = db.get(Chapter, ct.chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter missing")
        stmt = (
            select(TranslationSegment)
            .where(TranslationSegment.chapter_translation_id == ct_id)
            .order_by(TranslationSegment.order_index.asc())
        )
        rows = db.execute(stmt).scalars().all()
        out: list[TranslationSegmentOut] = []
        for r in rows:
            src = chapter.normalized_text[r.start : r.end]
            out.append(
                TranslationSegmentOut(
                    start=r.start,
                    end=r.end,
                    order_index=r.order_index,
                    src=src,
                    tgt=r.tgt,
                    flags=r.flags or [],
                )
            )
        return out

