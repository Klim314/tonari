from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import SessionLocal
from app.schemas import (
    ChapterGroupAddMembersRequest,
    ChapterGroupCreateRequest,
    ChapterGroupDetailOut,
    ChapterGroupMemberOut,
    ChapterGroupOut,
    ChapterGroupUpdateRequest,
    ChapterGroupMembersUpdateRequest,
    ChapterOut,
)
from services.chapter_groups import ChapterGroupsService
from services.exceptions import (
    ChapterGroupConflictError,
    ChapterGroupNotFoundError,
    ChapterNotFoundError,
)

router = APIRouter()


@router.post("/{work_id}/chapter-groups", response_model=ChapterGroupDetailOut, status_code=201)
def create_chapter_group(work_id: int, payload: ChapterGroupCreateRequest):
    """Create a new chapter group."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        try:
            group = service.create_group(
                work_id=work_id, name=payload.name, chapter_ids=payload.chapter_ids
            )
        except ChapterNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        except ChapterGroupConflictError as e:
            raise HTTPException(status_code=409, detail=str(e)) from None

        # Load detail with members
        group = service.get_group_detail(group.id)
        return _build_group_detail_response(group)


@router.get("/{work_id}/chapter-groups", response_model=list[ChapterGroupOut])
def list_chapter_groups(work_id: int):
    """List all chapter groups for a work."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        groups = service.list_groups(work_id)
        return [
            ChapterGroupOut(
                id=g.id,
                work_id=g.work_id,
                name=g.name,
                created_at=g.created_at,
                updated_at=g.updated_at,
                member_count=len(g.members),
                min_sort_key=float(min(m.chapter.sort_key for m in g.members)) if g.members else 0.0,
                item_type="group",
            )
            for g in groups
        ]


@router.get("/{work_id}/chapter-groups/{group_id}", response_model=ChapterGroupDetailOut)
def get_chapter_group(work_id: int, group_id: int):
    """Get chapter group details with members."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        try:
            group = service.get_group_detail(group_id)
        except ChapterGroupNotFoundError:
            raise HTTPException(status_code=404, detail="Group not found") from None

        if group.work_id != work_id:
            raise HTTPException(status_code=404, detail="Group not found")

        return _build_group_detail_response(group)


@router.patch("/{work_id}/chapter-groups/{group_id}", response_model=ChapterGroupDetailOut)
def update_chapter_group(work_id: int, group_id: int, payload: ChapterGroupUpdateRequest):
    """Update chapter group name."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        try:
            group = service.get_group_detail(group_id)
        except ChapterGroupNotFoundError:
            raise HTTPException(status_code=404, detail="Group not found") from None

        if group.work_id != work_id:
            raise HTTPException(status_code=404, detail="Group not found")

        if payload.name:
            group = service.update_group_name(group_id, payload.name)

        group = service.get_group_detail(group_id)
        return _build_group_detail_response(group)


@router.put("/{work_id}/chapter-groups/{group_id}/members", response_model=ChapterGroupDetailOut)
def update_chapter_group_members(
    work_id: int, group_id: int, payload: ChapterGroupMembersUpdateRequest
):
    """Update chapter group members (replace all)."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        try:
            group = service.get_group_detail(group_id)
        except ChapterGroupNotFoundError:
            raise HTTPException(status_code=404, detail="Group not found") from None

        if group.work_id != work_id:
            raise HTTPException(status_code=404, detail="Group not found")

        try:
            group = service.update_group_members(group_id, payload.chapter_ids)
        except ChapterNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        except ChapterGroupConflictError as e:
            raise HTTPException(status_code=409, detail=str(e)) from None

        group = service.get_group_detail(group_id)
        return _build_group_detail_response(group)


@router.post("/{work_id}/chapter-groups/{group_id}/members", response_model=ChapterGroupDetailOut)
def add_chapters_to_group(
    work_id: int, group_id: int, payload: ChapterGroupAddMembersRequest
):
    """Add chapters to an existing group."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        try:
            group = service.get_group_detail(group_id)
        except ChapterGroupNotFoundError:
            raise HTTPException(status_code=404, detail="Group not found") from None

        if group.work_id != work_id:
            raise HTTPException(status_code=404, detail="Group not found")

        try:
            group = service.add_chapters_to_group(group_id, payload.chapter_ids)
        except ChapterNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        except ChapterGroupConflictError as e:
            raise HTTPException(status_code=409, detail=str(e)) from None

        group = service.get_group_detail(group_id)
        return _build_group_detail_response(group)


@router.delete("/{work_id}/chapter-groups/{group_id}", status_code=204)
def delete_chapter_group(work_id: int, group_id: int):
    """Delete a chapter group."""
    with SessionLocal() as db:
        service = ChapterGroupsService(db)
        try:
            group = service.get_group_detail(group_id)
        except ChapterGroupNotFoundError:
            raise HTTPException(status_code=404, detail="Group not found") from None

        if group.work_id != work_id:
            raise HTTPException(status_code=404, detail="Group not found")

        service.delete_group(group_id)
        return None


def _build_group_detail_response(group) -> ChapterGroupDetailOut:
    """Helper to build group detail response."""
    members = [
        ChapterGroupMemberOut(
            id=member.id,
            chapter_id=member.chapter_id,
            order_index=member.order_index,
            chapter=ChapterOut.model_validate(member.chapter),
        )
        for member in sorted(group.members, key=lambda m: m.order_index)
    ]

    min_sort_key = min(m.chapter.sort_key for m in members) if members else 0.0

    return ChapterGroupDetailOut(
        id=group.id,
        work_id=group.work_id,
        name=group.name,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=len(members),
        min_sort_key=float(min_sort_key),
        item_type="group",
        members=members,
    )
