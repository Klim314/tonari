from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Chapter, Work


def seed_demo_chapter() -> tuple[int, int]:
    with SessionLocal() as session:
        work = Work(title="Sanity Work", source_meta={"source": "sanity"})
        session.add(work)
        session.flush()

        chapter = Chapter(
            work_id=work.id,
            idx=1,
            sort_key=Decimal(1),
            title="Chapter 1",
            normalized_text="彼は歩く。彼女も歩く。",
            text_hash="sanity",
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        return work.id, chapter.id


def run_sanity_checks() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    work_id, chapter_id = seed_demo_chapter()

    with TestClient(app) as client:
        health = client.get("/health")
        if health.status_code != 200:
            msg = f"Health check failed: {health.status_code} {health.text}"
            raise SystemExit(msg)
        print("✓ /health responded OK")

        resp = client.get(f"/works/{work_id}/chapters/{chapter_id}/translate/stream")
        if resp.status_code != 200:
            msg = f"Streaming translation failed: {resp.status_code} {resp.text}"
            raise SystemExit(msg)
        if "event: translation-complete" not in resp.text:
            raise SystemExit("Streaming translation did not complete")
        print(f"✓ Streamed chapter translation for work #{work_id}, chapter #{chapter_id}")

        segments = client.get(f"/works/{work_id}/chapters/{chapter_id}/translation")
        if segments.status_code != 200 or not segments.json()["segments"]:
            msg = f"Translation state fetch failed: {segments.status_code} {segments.text}"
            raise SystemExit(msg)
        print(f"✓ Retrieved {len(segments.json()['segments'])} translated segments")


if __name__ == "__main__":
    run_sanity_checks()
