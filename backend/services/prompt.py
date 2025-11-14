from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Prompt, PromptVersion, WorkPrompt
from .exceptions import PromptNotFoundError, PromptVersionNotFoundError
from .utils import sanitize_pagination


class PromptService:
    """Encapsulates queries and operations for Prompt and PromptVersion entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_prompts(
        self, q: str | None = None, limit: int = 50, offset: int = 0, max_limit: int = 100
    ) -> Tuple[List[Prompt], int, int, int]:
        """Search and list all prompts globally.

        Args:
            q: Optional search query to filter by prompt name
            limit: Number of results to return
            offset: Pagination offset
            max_limit: Maximum allowed limit

        Returns:
            Tuple of (prompts, total_count, limit, offset)
        """
        limit, offset = sanitize_pagination(limit, offset, max_limit=max_limit)

        stmt = select(Prompt).where(Prompt.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Prompt).where(Prompt.deleted_at.is_(None))

        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Prompt.name).like(like))
            count_stmt = count_stmt.where(func.lower(Prompt.name).like(like))

        stmt = stmt.order_by(Prompt.created_at.desc(), Prompt.id.desc()).limit(limit).offset(offset)
        rows = self.session.execute(stmt).scalars().all()
        total = self.session.execute(count_stmt).scalar_one()

        return list(rows), total, limit, offset

    def get_prompt(self, prompt_id: int, *, include_deleted: bool = False) -> Prompt:
        """Fetch a single prompt by ID.

        Args:
            prompt_id: The prompt ID

        Returns:
            Prompt object

        Raises:
            PromptNotFoundError: If prompt not found
        """
        prompt = self.session.get(Prompt, prompt_id)
        if not prompt or (not include_deleted and prompt.deleted_at is not None):
            raise PromptNotFoundError(f"prompt {prompt_id} not found")
        return prompt

    def get_prompt_for_work(self, work_id: int) -> Prompt | None:
        """Fetch the prompt assigned to a work.

        Args:
            work_id: The work ID

        Returns:
            Prompt object if assigned, None otherwise
        """
        stmt = (
            select(Prompt)
            .join(WorkPrompt)
            .where(WorkPrompt.work_id == work_id, Prompt.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_prompt(self, name: str, description: str | None = None) -> Prompt:
        """Create a new global prompt.

        Args:
            name: Prompt name
            description: Optional description

        Returns:
            Created Prompt object
        """
        prompt = Prompt(name=name, description=description)
        self.session.add(prompt)
        self.session.flush()
        self.session.commit()
        self.session.refresh(prompt)
        return prompt

    def update_prompt(
        self, prompt_id: int, name: str | None = None, description: str | None = None
    ) -> Prompt:
        """Update prompt metadata.

        Args:
            prompt_id: The prompt ID
            name: New name (optional)
            description: New description (optional)

        Returns:
            Updated Prompt object

        Raises:
            PromptNotFoundError: If prompt not found
        """
        prompt = self.get_prompt(prompt_id)
        if name is not None:
            prompt.name = name
        if description is not None:
            prompt.description = description
        self.session.add(prompt)
        self.session.commit()
        self.session.refresh(prompt)
        return prompt

    def soft_delete_prompt(self, prompt_id: int) -> None:
        """Soft delete a prompt by marking deleted_at."""

        prompt = self.get_prompt(prompt_id)
        if prompt.deleted_at is not None:
            return
        prompt.deleted_at = datetime.now(timezone.utc)
        self.session.add(prompt)
        self.session.commit()

    def get_prompt_versions(
        self, prompt_id: int, limit: int = 50, offset: int = 0, max_limit: int = 100
    ) -> Tuple[List[PromptVersion], int, int, int]:
        """List all versions for a prompt.

        Args:
            prompt_id: The prompt ID
            limit: Number of results to return
            offset: Pagination offset
            max_limit: Maximum allowed limit

        Returns:
            Tuple of (versions, total_count, limit, offset)

        Raises:
            PromptNotFoundError: If prompt not found
        """
        # Verify prompt exists
        self.get_prompt(prompt_id)

        limit, offset = sanitize_pagination(limit, offset, max_limit=max_limit)

        stmt = select(PromptVersion).where(PromptVersion.prompt_id == prompt_id)
        count_stmt = (
            select(func.count())
            .select_from(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
        )

        stmt = stmt.order_by(PromptVersion.version_number.desc()).limit(limit).offset(offset)
        rows = self.session.execute(stmt).scalars().all()
        total = self.session.execute(count_stmt).scalar_one()

        return rows, total, limit, offset

    def get_prompt_version(self, prompt_id: int, version_id: int) -> PromptVersion:
        """Fetch a specific version of a prompt.

        Args:
            prompt_id: The prompt ID
            version_id: The version ID

        Returns:
            PromptVersion object

        Raises:
            PromptNotFoundError: If prompt not found
            PromptVersionNotFoundError: If version not found
        """
        # Verify prompt exists
        self.get_prompt(prompt_id)

        version = self.session.get(PromptVersion, version_id)
        if not version or version.prompt_id != prompt_id:
            raise PromptVersionNotFoundError(
                f"version {version_id} not found for prompt {prompt_id}"
            )
        return version

    def append_version(
        self,
        prompt_id: int,
        model: str,
        template: str,
        parameters: dict | None = None,
        created_by: str | None = None,
    ) -> PromptVersion:
        """Append a new version to a prompt.

        Args:
            prompt_id: The prompt ID
            model: Model name (e.g., "gpt-4")
            template: F-string template for the prompt
            parameters: Optional metadata parameters
            created_by: Optional creator identifier

        Returns:
            Created PromptVersion object

        Raises:
            PromptNotFoundError: If prompt not found
        """
        prompt = self.get_prompt(prompt_id)

        # Get the next version number
        max_version = (
            self.session.execute(
                select(func.max(PromptVersion.version_number)).where(
                    PromptVersion.prompt_id == prompt_id
                )
            ).scalar()
            or 0
        )

        version = PromptVersion(
            prompt_id=prompt_id,
            version_number=max_version + 1,
            model=model,
            template=template,
            parameters=parameters,
            created_by=created_by,
        )
        self.session.add(version)
        self.session.flush()
        self.session.commit()
        self.session.refresh(version)
        return version
