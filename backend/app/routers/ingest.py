import hashlib
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Chapter, Work
from app.schemas import ChapterOut, IngestSyosetuRequest, WorkOut
from app.syosetu.scraper import SyosetuScraper

router = APIRouter()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


scraper = SyosetuScraper()


@router.post("/syosetu", response_model=ChapterOut)
async def ingest_syosetu(req: IngestSyosetuRequest):
    try:
        url = _build_chapter_url(req.novel_id, req.chapter)
        title, normalized_text = await run_in_threadpool(scraper.scrape_chapter, url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to fetch/parse: {e}")

    text_hash = _hash_text(normalized_text)

    with SessionLocal() as db:  # type: Session
        # For prototype, create a Work per ingest if not exists for the URL hash
        work_title = title
        source_meta = {
            "source": "syosetu",
            "novel_id": req.novel_id,
            "chapter": req.chapter,
            "url": url,
        }

        work = Work(title=work_title, source_meta=source_meta)
        db.add(work)
        db.flush()

        # idx = next chapter number for this work
        idx = 1
        stmt = select(Chapter).where(Chapter.work_id == work.id)
        existing = db.execute(stmt).scalars().all()
        if existing:
            idx = max(c.idx for c in existing) + 1

        chapter = Chapter(
            work_id=work.id,
            idx=idx,
            sort_key=Decimal(idx),
            title=title,
            normalized_text=normalized_text,
            text_hash=text_hash,
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)

        return ChapterOut.model_validate(chapter)


def _build_chapter_url(novel_id: str, chapter: int) -> str:
    novel = novel_id.strip().lower()
    return f"https://ncode.syosetu.com/{novel}/{chapter}/"
