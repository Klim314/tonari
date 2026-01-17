from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Chapter, ChapterGroup, ChapterGroupMember

from .exceptions import (
    ChapterGroupConflictError,
    ChapterGroupNotFoundError,
    ChapterNotFoundError,
)
from .utils import sanitize_pagination


class ChapterGroupsService:
    """Service for managing chapter groups."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_group(self, work_id: int, name: str, chapter_ids: list[int]) -> ChapterGroup:
        """Create a new group with chapters.

        Validates:
        - All chapters exist and belong to work
        - No chapters already in another group (409 Conflict)
        """
        # Validate chapters exist and belong to work
        stmt = select(Chapter).where(Chapter.id.in_(chapter_ids), Chapter.work_id == work_id)
        chapters = list(self.session.execute(stmt).scalars().all())

        if len(chapters) != len(chapter_ids):
            found_ids = {ch.id for ch in chapters}
            missing_ids = set(chapter_ids) - found_ids
            raise ChapterNotFoundError(
                f"Chapters {missing_ids} not found or don't belong to work {work_id}"
            )

        # Check for existing group membership
        existing_stmt = select(ChapterGroupMember.chapter_id).where(
            ChapterGroupMember.chapter_id.in_(chapter_ids)
        )
        existing_members = list(self.session.execute(existing_stmt).scalars().all())
        if existing_members:
            raise ChapterGroupConflictError(
                f"Chapters {existing_members} already belong to another group"
            )

        # Create group
        group = ChapterGroup(work_id=work_id, name=name)
        self.session.add(group)
        self.session.flush()

        # Add members in specified order
        for idx, chapter_id in enumerate(chapter_ids):
            member = ChapterGroupMember(
                group_id=group.id, chapter_id=chapter_id, order_index=idx
            )
            self.session.add(member)

        self.session.commit()
        self.session.refresh(group)
        return group

    def get_group_detail(self, group_id: int) -> ChapterGroup:
        """Get group with members (joinedload)."""
        stmt = (
            select(ChapterGroup)
            .where(ChapterGroup.id == group_id)
            .options(
                joinedload(ChapterGroup.members).joinedload(ChapterGroupMember.chapter)
            )
        )
        group = self.session.execute(stmt).unique().scalar_one_or_none()
        if not group:
            raise ChapterGroupNotFoundError(f"Group {group_id} not found")
        return group

    def list_groups(self, work_id: int) -> list[ChapterGroup]:
        """List all groups for a work with their members."""
        stmt = (
            select(ChapterGroup)
            .where(ChapterGroup.work_id == work_id)
            .options(
                joinedload(ChapterGroup.members).joinedload(ChapterGroupMember.chapter)
            )
            .order_by(ChapterGroup.name)
        )
        return list(self.session.execute(stmt).scalars().unique().all())

    def get_chapters_with_groups(
        self, work_id: int, limit: int = 10, offset: int = 0
    ) -> Tuple[list[tuple[str, ChapterGroup | Chapter, Decimal]], int, int, int, int, int]:
        """Get mixed list of groups and ungrouped chapters, sorted by sort_key.

        Returns:
            (items, total_chapters, total_groups, total_items, limit, offset)
            where items is list of tuples: (item_type, data, sort_key)
        """
        limit, offset = sanitize_pagination(limit, offset, max_limit=100)

        # 1. Fetch all groups for work with members
        groups_stmt = (
            select(ChapterGroup)
            .where(ChapterGroup.work_id == work_id)
            .options(
                joinedload(ChapterGroup.members).joinedload(ChapterGroupMember.chapter)
            )
        )
        groups = list(self.session.execute(groups_stmt).scalars().unique().all())

        # 2. Calculate min_sort_key for each group and create items list
        group_items = []
        grouped_chapter_ids = set()
        for group in groups:
            if group.members:
                min_sort_key = min(member.chapter.sort_key for member in group.members)
                group_items.append(("group", group, min_sort_key))
                grouped_chapter_ids.update(member.chapter_id for member in group.members)

        # 3. Fetch all ungrouped chapters
        ungrouped_stmt = (
            select(Chapter)
            .where(
                Chapter.work_id == work_id,
                ~Chapter.id.in_(grouped_chapter_ids) if grouped_chapter_ids else True,
            )
            .order_by(Chapter.sort_key.asc(), Chapter.idx.asc(), Chapter.id.asc())
        )
        ungrouped_chapters = list(self.session.execute(ungrouped_stmt).scalars().all())

        # Create chapter items
        chapter_items = [("chapter", ch, ch.sort_key) for ch in ungrouped_chapters]

        # 4. Merge and sort by sort_key
        all_items = sorted(group_items + chapter_items, key=lambda x: x[2])

        # 5. Count totals
        total_chapters = len(ungrouped_chapters) + sum(
            len(g.members) for _, g, _ in group_items
        )
        total_groups = len(group_items)
        total_items = len(all_items)  # Total number of items in the mixed list

        # 6. Apply pagination
        paginated_items = all_items[offset : offset + limit]

        return paginated_items, total_chapters, total_groups, total_items, limit, offset

    def update_group_name(self, group_id: int, name: str) -> ChapterGroup:
        """Update group name."""
        group = self.session.get(ChapterGroup, group_id)
        if not group:
            raise ChapterGroupNotFoundError(f"Group {group_id} not found")

        group.name = name
        self.session.commit()
        self.session.refresh(group)
        return group

    def update_group_members(self, group_id: int, chapter_ids: list[int]) -> ChapterGroup:
        """Replace all members with new list (order preserved).

        Validates no conflicts with other groups.
        """
        group = self.session.get(ChapterGroup, group_id)
        if not group:
            raise ChapterGroupNotFoundError(f"Group {group_id} not found")

        # Validate chapters exist and belong to same work
        stmt = select(Chapter).where(
            Chapter.id.in_(chapter_ids), Chapter.work_id == group.work_id
        )
        chapters = list(self.session.execute(stmt).scalars().all())

        if len(chapters) != len(chapter_ids):
            found_ids = {ch.id for ch in chapters}
            missing_ids = set(chapter_ids) - found_ids
            raise ChapterNotFoundError(f"Chapters {missing_ids} not found")

        # Check for conflicts (excluding current group)
        existing_stmt = select(ChapterGroupMember).where(
            ChapterGroupMember.chapter_id.in_(chapter_ids),
            ChapterGroupMember.group_id != group_id,
        )
        conflicts = list(self.session.execute(existing_stmt).scalars().all())
        if conflicts:
            conflict_ids = [m.chapter_id for m in conflicts]
            raise ChapterGroupConflictError(
                f"Chapters {conflict_ids} belong to another group"
            )

        # Delete existing members
        delete_stmt = select(ChapterGroupMember).where(
            ChapterGroupMember.group_id == group_id
        )
        for member in self.session.execute(delete_stmt).scalars():
            self.session.delete(member)

        # Flush to ensure deletes are committed before inserts (avoid unique constraint violations)
        self.session.flush()

        # Add new members
        for idx, chapter_id in enumerate(chapter_ids):
            member = ChapterGroupMember(
                group_id=group.id, chapter_id=chapter_id, order_index=idx
            )
            self.session.add(member)

        self.session.commit()
        self.session.refresh(group)
        return group

    def add_chapters_to_group(self, group_id: int, chapter_ids: list[int]) -> ChapterGroup:
        """Add chapters to an existing group.

        Validates:
        - Group exists
        - All chapters exist and belong to same work as group
        - No chapters already in another group (409 Conflict)
        - Chapters not already in this group (skip duplicates silently)
        """
        group = self.session.get(ChapterGroup, group_id)
        if not group:
            raise ChapterGroupNotFoundError(f"Group {group_id} not found")

        # Validate chapters exist and belong to same work
        stmt = select(Chapter).where(
            Chapter.id.in_(chapter_ids), Chapter.work_id == group.work_id
        )
        chapters = list(self.session.execute(stmt).scalars().all())

        if len(chapters) != len(chapter_ids):
            found_ids = {ch.id for ch in chapters}
            missing_ids = set(chapter_ids) - found_ids
            raise ChapterNotFoundError(
                f"Chapters {missing_ids} not found or don't belong to work {group.work_id}"
            )

        # Check for conflicts with OTHER groups
        existing_stmt = select(ChapterGroupMember).where(
            ChapterGroupMember.chapter_id.in_(chapter_ids),
            ChapterGroupMember.group_id != group_id,
        )
        conflicts = list(self.session.execute(existing_stmt).scalars().all())
        if conflicts:
            conflict_ids = [m.chapter_id for m in conflicts]
            raise ChapterGroupConflictError(
                f"Chapters {conflict_ids} already belong to another group"
            )

        # Get current members and max order_index
        current_members_stmt = select(ChapterGroupMember).where(
            ChapterGroupMember.group_id == group_id
        )
        current_members = list(self.session.execute(current_members_stmt).scalars().all())
        already_in_group = {m.chapter_id for m in current_members}
        max_order = max((m.order_index for m in current_members), default=-1)

        # Add new members (skip those already in group)
        new_chapter_ids = [cid for cid in chapter_ids if cid not in already_in_group]
        for idx, chapter_id in enumerate(new_chapter_ids):
            member = ChapterGroupMember(
                group_id=group.id,
                chapter_id=chapter_id,
                order_index=max_order + 1 + idx,
            )
            self.session.add(member)

        self.session.commit()
        self.session.refresh(group)
        return group

    def delete_group(self, group_id: int) -> None:
        """Delete group (cascade deletes members)."""
        group = self.session.get(ChapterGroup, group_id)
        if not group:
            raise ChapterGroupNotFoundError(f"Group {group_id} not found")

        self.session.delete(group)
        self.session.commit()

    def get_chapter_group_membership(self, chapter_id: int) -> Optional[ChapterGroup]:
        """Get the group a chapter belongs to (if any)."""
        stmt = (
            select(ChapterGroup)
            .join(ChapterGroupMember)
            .where(ChapterGroupMember.chapter_id == chapter_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()
