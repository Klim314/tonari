from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Chapter, Work


def _create_work(session: Session, title: str, chapter_count: int = 0) -> Work:
    work = Work(title=title, source_meta={"source": "test"})
    session.add(work)
    session.flush()

    for i in range(chapter_count):
        chapter = Chapter(
            work_id=work.id,
            idx=i + 1,
            title=f"{title} #{i+1}",
            normalized_text=f"chapter {i+1}",
            text_hash=f"{title}-{i+1}",
        )
        session.add(chapter)
    session.commit()
    session.refresh(work)
    return work


def test_search_works_pagination(client, db_session):
    _create_work(db_session, "Beta")
    _create_work(db_session, "Alpha")
    _create_work(db_session, "Gamma")

    resp = client.get("/works?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    titles = [item["title"] for item in data["items"]]
    assert titles == ["Alpha", "Beta"]

    resp_page2 = client.get("/works?limit=2&offset=2")
    assert resp_page2.status_code == 200
    data2 = resp_page2.json()
    assert data2["items"][0]["title"] == "Gamma"


def test_search_works_filter(client, db_session):
    _create_work(db_session, "Alpha Tales")
    _create_work(db_session, "Beta Story")

    resp = client.get("/works?q=alpha")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Alpha Tales"


def test_list_chapters_for_work(client, db_session):
    work = _create_work(db_session, "Chronicles", chapter_count=3)

    resp = client.get(f"/works/{work.id}/chapters?limit=2")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 3
    assert payload["items"][0]["title"] == "Chronicles #1"
    assert payload["items"][1]["idx"] == 2

    resp2 = client.get(f"/works/{work.id}/chapters?offset=2")
    assert resp2.status_code == 200
    payload2 = resp2.json()
    assert len(payload2["items"]) == 1
    assert payload2["items"][0]["idx"] == 3


def test_list_chapters_for_missing_work(client):
    resp = client.get("/works/999/chapters")
    assert resp.status_code == 404
