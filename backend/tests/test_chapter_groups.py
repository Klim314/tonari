"""Tests for chapter groups functionality."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Chapter, ChapterGroup, ChapterGroupMember, Work
from services.chapter_groups import ChapterGroupsService
from services.exceptions import (
    ChapterGroupConflictError,
    ChapterGroupNotFoundError,
    ChapterNotFoundError,
)


def _create_work(db_session) -> Work:
    """Helper to create a test work."""
    work = Work(title="Test Work", source="fake", source_id="test-1")
    db_session.add(work)
    db_session.commit()
    return work


def _create_chapters(db_session, work: Work, count: int = 5) -> list[Chapter]:
    """Helper to create test chapters."""
    chapters = []
    for i in range(1, count + 1):
        chapter = Chapter(
            work_id=work.id,
            idx=i,
            sort_key=Decimal(f"{i}.0000"),
            title=f"Chapter {i}",
            normalized_text=f"Body {i}",
            text_hash=f"hash{i}",
        )
        db_session.add(chapter)
        chapters.append(chapter)
    db_session.commit()
    return chapters


# Service layer tests


def test_create_group_success(db_session):
    """Test creating a group with valid chapters."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)
    chapter_ids = [chapters[0].id, chapters[1].id, chapters[2].id]

    service = ChapterGroupsService(db_session)
    group = service.create_group(work.id, "Arc 1", chapter_ids)

    assert group.id is not None
    assert group.name == "Arc 1"
    assert group.work_id == work.id

    # Verify members were created
    members = db_session.execute(
        select(ChapterGroupMember).where(ChapterGroupMember.group_id == group.id)
    ).scalars().all()
    assert len(members) == 3
    assert [m.chapter_id for m in sorted(members, key=lambda x: x.order_index)] == chapter_ids


def test_create_group_with_nonexistent_chapters(db_session):
    """Test creating a group with chapters that don't exist."""
    work = _create_work(db_session)
    _create_chapters(db_session, work, count=2)

    service = ChapterGroupsService(db_session)
    with pytest.raises(ChapterNotFoundError, match="not found"):
        service.create_group(work.id, "Arc 1", [999, 1000])


def test_create_group_with_chapters_from_different_work(db_session):
    """Test creating a group with chapters from a different work."""
    work1 = _create_work(db_session)
    work2 = Work(title="Other Work", source="fake", source_id="test-2")
    db_session.add(work2)
    db_session.commit()

    chapters1 = _create_chapters(db_session, work1, count=2)
    chapters2 = _create_chapters(db_session, work2, count=2)

    service = ChapterGroupsService(db_session)
    with pytest.raises(ChapterNotFoundError, match="not found"):
        service.create_group(work1.id, "Arc 1", [chapters1[0].id, chapters2[0].id])


def test_create_group_with_already_grouped_chapter(db_session):
    """Test creating a group when a chapter is already in another group."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    service = ChapterGroupsService(db_session)
    # Create first group
    service.create_group(work.id, "Arc 1", [chapters[0].id, chapters[1].id])

    # Try to create second group with overlapping chapter
    with pytest.raises(ChapterGroupConflictError, match="already belong"):
        service.create_group(work.id, "Arc 2", [chapters[1].id, chapters[2].id])


def test_get_group_detail(db_session):
    """Test fetching group details with members."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    service = ChapterGroupsService(db_session)
    group = service.create_group(work.id, "Arc 1", [chapters[0].id, chapters[1].id])

    # Expire all to clear session state before joinedload
    db_session.expire_all()

    # Fetch detail
    detail = service.get_group_detail(group.id)
    assert detail.id == group.id
    assert detail.name == "Arc 1"
    assert len(detail.members) == 2
    assert detail.members[0].chapter.title == "Chapter 1"
    assert detail.members[1].chapter.title == "Chapter 2"


def test_get_group_detail_not_found(db_session):
    """Test fetching a non-existent group."""
    service = ChapterGroupsService(db_session)
    with pytest.raises(ChapterGroupNotFoundError):
        service.get_group_detail(999)


def test_update_group_name(db_session):
    """Test updating a group's name."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=2)

    service = ChapterGroupsService(db_session)
    group = service.create_group(work.id, "Old Name", [chapters[0].id])

    updated = service.update_group_name(group.id, "New Name")
    assert updated.name == "New Name"

    # Verify in database
    db_session.refresh(group)
    assert group.name == "New Name"


def test_update_group_name_not_found(db_session):
    """Test updating a non-existent group's name."""
    service = ChapterGroupsService(db_session)
    with pytest.raises(ChapterGroupNotFoundError):
        service.update_group_name(999, "New Name")


def test_update_group_members(db_session):
    """Test replacing all members of a group."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    service = ChapterGroupsService(db_session)
    group = service.create_group(work.id, "Arc 1", [chapters[0].id, chapters[1].id])

    # Replace members
    service.update_group_members(group.id, [chapters[2].id, chapters[3].id, chapters[4].id])

    # Expire all to clear session state before joinedload
    db_session.expire_all()

    # Verify members changed
    detail = service.get_group_detail(group.id)
    assert len(detail.members) == 3
    member_chapter_ids = [m.chapter_id for m in detail.members]
    assert chapters[0].id not in member_chapter_ids
    assert chapters[1].id not in member_chapter_ids
    assert chapters[2].id in member_chapter_ids
    assert chapters[3].id in member_chapter_ids
    assert chapters[4].id in member_chapter_ids


def test_update_group_members_conflict(db_session):
    """Test updating members with a chapter that's in another group."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    service = ChapterGroupsService(db_session)
    group1 = service.create_group(work.id, "Arc 1", [chapters[0].id])
    group2 = service.create_group(work.id, "Arc 2", [chapters[1].id])

    # Try to add chapter from group1 to group2
    with pytest.raises(ChapterGroupConflictError, match="belong to another group"):
        service.update_group_members(group2.id, [chapters[0].id, chapters[1].id])


def test_delete_group(db_session):
    """Test deleting a group."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=3)

    service = ChapterGroupsService(db_session)
    group = service.create_group(work.id, "Arc 1", [chapters[0].id, chapters[1].id])

    # Delete group
    service.delete_group(group.id)

    # Verify group deleted
    with pytest.raises(ChapterGroupNotFoundError):
        service.get_group_detail(group.id)

    # Verify members deleted (cascade)
    members = db_session.execute(
        select(ChapterGroupMember).where(ChapterGroupMember.group_id == group.id)
    ).scalars().all()
    assert len(members) == 0


def test_delete_group_not_found(db_session):
    """Test deleting a non-existent group."""
    service = ChapterGroupsService(db_session)
    with pytest.raises(ChapterGroupNotFoundError):
        service.delete_group(999)


def test_get_chapter_group_membership(db_session):
    """Test finding which group a chapter belongs to."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    service = ChapterGroupsService(db_session)
    group = service.create_group(work.id, "Arc 1", [chapters[0].id, chapters[1].id])

    # Chapter in group
    membership = service.get_chapter_group_membership(chapters[0].id)
    assert membership is not None
    assert membership.id == group.id

    # Chapter not in group
    membership = service.get_chapter_group_membership(chapters[2].id)
    assert membership is None


def test_get_chapters_with_groups_mixed_list(db_session):
    """Test fetching mixed list of groups and ungrouped chapters."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    service = ChapterGroupsService(db_session)
    # Create group with chapters 2 and 3 (sort_key 2.0 and 3.0)
    service.create_group(work.id, "Arc 1", [chapters[1].id, chapters[2].id])

    items, total_chapters, total_groups, total_items, limit, offset = service.get_chapters_with_groups(
        work.id, limit=10, offset=0
    )

    # Should have 4 items: Chapter 1 (ungrouped), Group (min 2.0), Chapter 4 (ungrouped), Chapter 5 (ungrouped)
    assert len(items) == 4
    assert total_chapters == 5
    assert total_groups == 1
    assert total_items == 4

    # Check sorting by sort_key
    item_types = [item[0] for item in items]
    sort_keys = [item[2] for item in items]

    assert item_types[0] == "chapter"  # Chapter 1
    assert sort_keys[0] == Decimal("1.0000")

    assert item_types[1] == "group"  # Arc 1 (min sort_key 2.0)
    assert sort_keys[1] == Decimal("2.0000")

    assert item_types[2] == "chapter"  # Chapter 4
    assert sort_keys[2] == Decimal("4.0000")

    assert item_types[3] == "chapter"  # Chapter 5
    assert sort_keys[3] == Decimal("5.0000")


def test_get_chapters_with_groups_sorting(db_session):
    """Test that groups are sorted correctly by minimum sort_key of members."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=7)

    service = ChapterGroupsService(db_session)
    # Create groups in reverse order to test sorting
    service.create_group(work.id, "Arc 2", [chapters[4].id, chapters[5].id])  # min 5.0
    service.create_group(work.id, "Arc 1", [chapters[1].id, chapters[2].id])  # min 2.0

    items, _, _, _, _, _ = service.get_chapters_with_groups(work.id, limit=10, offset=0)

    # Should be: Chapter 1, Arc 1 (min 2.0), Chapter 4, Arc 2 (min 5.0), Chapter 7
    assert len(items) == 5

    expected_order = [
        ("chapter", Decimal("1.0000")),
        ("group", Decimal("2.0000")),
        ("chapter", Decimal("4.0000")),
        ("group", Decimal("5.0000")),
        ("chapter", Decimal("7.0000")),
    ]

    for i, (expected_type, expected_key) in enumerate(expected_order):
        assert items[i][0] == expected_type
        assert items[i][2] == expected_key


def test_get_chapters_with_groups_pagination(db_session):
    """Test pagination of mixed list."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=10)

    service = ChapterGroupsService(db_session)
    service.create_group(work.id, "Arc 1", [chapters[2].id, chapters[3].id])  # min 3.0

    # First page (limit 5)
    items_page1, _, _, _, limit, offset = service.get_chapters_with_groups(
        work.id, limit=5, offset=0
    )
    assert len(items_page1) == 5
    assert limit == 5
    assert offset == 0

    # Second page
    items_page2, _, _, _, limit, offset = service.get_chapters_with_groups(
        work.id, limit=5, offset=5
    )
    assert len(items_page2) == 4  # 9 total items - 5 = 4
    assert limit == 5
    assert offset == 5


def test_get_chapters_with_groups_only_groups(db_session):
    """Test when all chapters are in groups."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=4)

    service = ChapterGroupsService(db_session)
    service.create_group(work.id, "Arc 1", [chapters[0].id, chapters[1].id])
    service.create_group(work.id, "Arc 2", [chapters[2].id, chapters[3].id])

    items, total_chapters, total_groups, total_items, _, _ = service.get_chapters_with_groups(
        work.id, limit=10, offset=0
    )

    # Should have 2 groups only
    assert len(items) == 2
    assert total_chapters == 4
    assert total_groups == 2
    assert total_items == 2
    assert all(item[0] == "group" for item in items)


def test_get_chapters_with_groups_no_groups(db_session):
    """Test when there are no groups."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=3)

    service = ChapterGroupsService(db_session)
    items, total_chapters, total_groups, total_items, _, _ = service.get_chapters_with_groups(
        work.id, limit=10, offset=0
    )

    # Should have 3 chapters only
    assert len(items) == 3
    assert total_chapters == 3
    assert total_groups == 0
    assert total_items == 3
    assert all(item[0] == "chapter" for item in items)


# API endpoint tests


def test_create_chapter_group_api(client, db_session):
    """Test POST /works/{work_id}/chapter-groups endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=3)

    payload = {
        "name": "Arc 1",
        "chapter_ids": [chapters[0].id, chapters[1].id],
    }

    response = client.post(f"/works/{work.id}/chapter-groups", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Arc 1"
    assert data["work_id"] == work.id
    assert data["member_count"] == 2
    assert len(data["members"]) == 2


def test_create_chapter_group_api_validation_error(client, db_session):
    """Test validation errors for create endpoint."""
    work = _create_work(db_session)

    # Empty name
    payload = {"name": "   ", "chapter_ids": [1]}
    response = client.post(f"/works/{work.id}/chapter-groups", json=payload)
    assert response.status_code == 422

    # Empty chapter_ids
    payload = {"name": "Arc 1", "chapter_ids": []}
    response = client.post(f"/works/{work.id}/chapter-groups", json=payload)
    assert response.status_code == 422


def test_create_chapter_group_api_chapter_not_found(client, db_session):
    """Test 400 error when chapters don't exist."""
    work = _create_work(db_session)

    payload = {"name": "Arc 1", "chapter_ids": [999, 1000]}
    response = client.post(f"/works/{work.id}/chapter-groups", json=payload)
    assert response.status_code == 400
    assert "not found" in response.json()["detail"]


def test_create_chapter_group_api_conflict(client, db_session):
    """Test 409 error when chapter already in another group."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=3)

    # Create first group
    payload1 = {"name": "Arc 1", "chapter_ids": [chapters[0].id]}
    client.post(f"/works/{work.id}/chapter-groups", json=payload1)

    # Try to create second group with same chapter
    payload2 = {"name": "Arc 2", "chapter_ids": [chapters[0].id, chapters[1].id]}
    response = client.post(f"/works/{work.id}/chapter-groups", json=payload2)
    assert response.status_code == 409
    assert "already belong" in response.json()["detail"]


def test_get_chapter_group_api(client, db_session):
    """Test GET /works/{work_id}/chapter-groups/{group_id} endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=2)

    # Create group via API
    payload = {"name": "Arc 1", "chapter_ids": [chapters[0].id, chapters[1].id]}
    create_resp = client.post(f"/works/{work.id}/chapter-groups", json=payload)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    response = client.get(f"/works/{work.id}/chapter-groups/{group_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Arc 1"
    assert len(data["members"]) == 2


def test_get_chapter_group_api_not_found(client, db_session):
    """Test 404 error when group doesn't exist."""
    work = _create_work(db_session)

    response = client.get(f"/works/{work.id}/chapter-groups/999")
    assert response.status_code == 404


def test_get_chapter_group_api_wrong_work(client, db_session):
    """Test 404 error when group belongs to different work."""
    work1 = _create_work(db_session)
    work2 = Work(title="Other Work", source="fake", source_id="test-2")
    db_session.add(work2)
    db_session.commit()

    chapters = _create_chapters(db_session, work1, count=2)

    # Create group via API
    payload = {"name": "Arc 1", "chapter_ids": [chapters[0].id]}
    create_resp = client.post(f"/works/{work1.id}/chapter-groups", json=payload)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # Try to access group via wrong work
    response = client.get(f"/works/{work2.id}/chapter-groups/{group_id}")
    assert response.status_code == 404


def test_update_chapter_group_name_api(client, db_session):
    """Test PATCH /works/{work_id}/chapter-groups/{group_id} endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=2)

    # Create group via API
    create_payload = {"name": "Old Name", "chapter_ids": [chapters[0].id]}
    create_resp = client.post(f"/works/{work.id}/chapter-groups", json=create_payload)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    payload = {"name": "New Name"}
    response = client.patch(f"/works/{work.id}/chapter-groups/{group_id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "New Name"


def test_update_chapter_group_members_api(client, db_session):
    """Test PUT /works/{work_id}/chapter-groups/{group_id}/members endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    # Create group via API
    create_payload = {"name": "Arc 1", "chapter_ids": [chapters[0].id, chapters[1].id]}
    create_resp = client.post(f"/works/{work.id}/chapter-groups", json=create_payload)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # Replace members
    payload = {"chapter_ids": [chapters[2].id, chapters[3].id, chapters[4].id]}
    response = client.put(
        f"/works/{work.id}/chapter-groups/{group_id}/members", json=payload
    )
    assert response.status_code == 200

    data = response.json()
    assert data["member_count"] == 3
    member_chapter_ids = [m["chapter_id"] for m in data["members"]]
    assert chapters[2].id in member_chapter_ids
    assert chapters[3].id in member_chapter_ids
    assert chapters[4].id in member_chapter_ids


def test_delete_chapter_group_api(client, db_session):
    """Test DELETE /works/{work_id}/chapter-groups/{group_id} endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=2)

    # Create group via API
    create_payload = {"name": "Arc 1", "chapter_ids": [chapters[0].id]}
    create_resp = client.post(f"/works/{work.id}/chapter-groups", json=create_payload)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    response = client.delete(f"/works/{work.id}/chapter-groups/{group_id}")
    assert response.status_code == 204

    # Verify deleted
    response = client.get(f"/works/{work.id}/chapter-groups/{group_id}")
    assert response.status_code == 404


def test_list_chapter_groups_api(client, db_session):
    """Test GET /works/{work_id}/chapter-groups endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    # Create two groups via API
    create_resp1 = client.post(
        f"/works/{work.id}/chapter-groups",
        json={"name": "Arc 1", "chapter_ids": [chapters[0].id, chapters[1].id]},
    )
    assert create_resp1.status_code == 201

    create_resp2 = client.post(
        f"/works/{work.id}/chapter-groups",
        json={"name": "Arc 2", "chapter_ids": [chapters[2].id]},
    )
    assert create_resp2.status_code == 201

    # List groups
    response = client.get(f"/works/{work.id}/chapter-groups")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    names = [g["name"] for g in data]
    assert "Arc 1" in names
    assert "Arc 2" in names

    # Check member counts
    arc1 = next(g for g in data if g["name"] == "Arc 1")
    arc2 = next(g for g in data if g["name"] == "Arc 2")
    assert arc1["member_count"] == 2
    assert arc2["member_count"] == 1


def test_list_chapter_groups_empty(client, db_session):
    """Test GET /works/{work_id}/chapter-groups with no groups."""
    work = _create_work(db_session)

    response = client.get(f"/works/{work.id}/chapter-groups")
    assert response.status_code == 200
    assert response.json() == []


def test_add_chapters_to_group_api(client, db_session):
    """Test POST /works/{work_id}/chapter-groups/{group_id}/members endpoint."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    # Create group with first 2 chapters
    create_resp = client.post(
        f"/works/{work.id}/chapter-groups",
        json={"name": "Arc 1", "chapter_ids": [chapters[0].id, chapters[1].id]},
    )
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]
    assert create_resp.json()["member_count"] == 2

    # Add 2 more chapters
    response = client.post(
        f"/works/{work.id}/chapter-groups/{group_id}/members",
        json={"chapter_ids": [chapters[2].id, chapters[3].id]},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["member_count"] == 4
    member_chapter_ids = [m["chapter_id"] for m in data["members"]]
    assert chapters[0].id in member_chapter_ids
    assert chapters[1].id in member_chapter_ids
    assert chapters[2].id in member_chapter_ids
    assert chapters[3].id in member_chapter_ids


def test_add_chapters_to_group_conflict(client, db_session):
    """Test adding chapters that belong to another group returns 409."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=4)

    # Create first group
    create_resp1 = client.post(
        f"/works/{work.id}/chapter-groups",
        json={"name": "Arc 1", "chapter_ids": [chapters[0].id, chapters[1].id]},
    )
    assert create_resp1.status_code == 201
    group1_id = create_resp1.json()["id"]

    # Create second group
    create_resp2 = client.post(
        f"/works/{work.id}/chapter-groups",
        json={"name": "Arc 2", "chapter_ids": [chapters[2].id]},
    )
    assert create_resp2.status_code == 201
    group2_id = create_resp2.json()["id"]

    # Try to add chapter from group1 to group2
    response = client.post(
        f"/works/{work.id}/chapter-groups/{group2_id}/members",
        json={"chapter_ids": [chapters[0].id]},
    )
    assert response.status_code == 409


def test_add_chapters_to_group_skip_duplicates(client, db_session):
    """Test adding chapters already in the group are silently skipped."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=3)

    # Create group with first chapter
    create_resp = client.post(
        f"/works/{work.id}/chapter-groups",
        json={"name": "Arc 1", "chapter_ids": [chapters[0].id]},
    )
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # Add first chapter again along with second chapter
    response = client.post(
        f"/works/{work.id}/chapter-groups/{group_id}/members",
        json={"chapter_ids": [chapters[0].id, chapters[1].id]},
    )
    assert response.status_code == 200

    data = response.json()
    # Should have 2 members, not 3 (duplicate skipped)
    assert data["member_count"] == 2


def test_chapters_list_with_groups_api(client, db_session):
    """Test GET /works/{work_id}/chapters returns mixed list."""
    work = _create_work(db_session)
    chapters = _create_chapters(db_session, work, count=5)

    # Create group via API
    create_payload = {"name": "Arc 1", "chapter_ids": [chapters[1].id, chapters[2].id]}
    create_resp = client.post(f"/works/{work.id}/chapter-groups", json=create_payload)
    assert create_resp.status_code == 201

    response = client.get(f"/works/{work.id}/chapters")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert data["total_chapters"] == 5
    assert data["total_groups"] == 1
    assert data["total_items"] == 4  # 3 ungrouped + 1 group

    # Verify item structure
    items = data["items"]
    assert len(items) == 4

    # First item should be Chapter 1 (ungrouped)
    assert items[0]["item_type"] == "chapter"
    assert items[0]["data"]["title"] == "Chapter 1"

    # Second item should be Arc 1 (group with min sort_key 2.0)
    assert items[1]["item_type"] == "group"
    assert items[1]["data"]["name"] == "Arc 1"
    assert items[1]["data"]["member_count"] == 2
