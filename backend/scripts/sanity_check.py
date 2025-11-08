from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Chapter, Work


def seed_demo_chapter() -> int:
    with SessionLocal() as session:
        work = Work(title="Sanity Work", source_meta={"source": "sanity"})
        session.add(work)
        session.flush()

        chapter = Chapter(
            work_id=work.id,
            idx=1,
            title="Chapter 1",
            normalized_text="彼は歩く。彼女も歩く。",
            text_hash="sanity",
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        return chapter.id


def run_sanity_checks() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    chapter_id = seed_demo_chapter()

    with TestClient(app) as client:
        health = client.get("/health")
        if health.status_code != 200:
            msg = f"Health check failed: {health.status_code} {health.text}"
            raise SystemExit(msg)
        print("✓ /health responded OK")

        resp = client.post("/chapter-translations/", json={"chapter_id": chapter_id})
        if resp.status_code != 200:
            msg = f"Translation creation failed: {resp.status_code} {resp.text}"
            raise SystemExit(msg)
        ct_id = resp.json()["id"]
        print(f"✓ Created chapter translation #{ct_id}")

        segments = client.get(f"/chapter-translations/{ct_id}/segments")
        if segments.status_code != 200 or not segments.json():
            msg = f"Segments fetch failed: {segments.status_code} {segments.text}"
            raise SystemExit(msg)
        print(f"✓ Retrieved {len(segments.json())} segments")


if __name__ == "__main__":
    run_sanity_checks()
