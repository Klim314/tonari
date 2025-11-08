from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import SessionLocal
from app.schemas import IngestSyosetuRequest, WorkOut, ChapterOut
from app.syosetu_client import SyosetuClient
from app.models import Work, Chapter
import hashlib


router = APIRouter()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@router.post("/syosetu", response_model=ChapterOut)
async def ingest_syosetu(req: IngestSyosetuRequest):
    client = SyosetuClient()
    try:
        html = await client.fetch(req.url)
        title, normalized_text = client.parse_chapter(html)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to fetch/parse: {e}")

    text_hash = _hash_text(normalized_text)

    with SessionLocal() as db:  # type: Session
        # For prototype, create a Work per ingest if not exists for the URL hash
        work_title = title
        source_meta = {"source": "syosetu", "url": req.url}

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
            title=title,
            normalized_text=normalized_text,
            text_hash=text_hash,
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)

        return ChapterOut.model_validate(chapter)
