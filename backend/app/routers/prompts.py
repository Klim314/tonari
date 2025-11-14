from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import SessionLocal
from app.schemas import (
    PaginatedPromptVersionsOut,
    PaginatedPromptsOut,
    PromptCreateRequest,
    PromptDetailOut,
    PromptOut,
    PromptUpdateRequest,
    PromptVersionCreateRequest,
    PromptVersionOut,
    WorkPromptUpdateRequest,
)
from services.exceptions import PromptNotFoundError, PromptVersionNotFoundError
from services.prompt import PromptService
from services.works import WorksService

router = APIRouter()


@router.get("/", response_model=PaginatedPromptsOut)
def list_prompts(q: str | None = Query(default=None), limit: int = 50, offset: int = 0):
    """List all prompts globally with optional search."""
    with SessionLocal() as db:
        service = PromptService(db)
        rows, total, limit, offset = service.get_prompts(q=q, limit=limit, offset=offset)
        return PaginatedPromptsOut(
            items=[PromptOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.post("/", response_model=PromptOut)
def create_prompt(req: PromptCreateRequest):
    """Create a new global prompt."""
    with SessionLocal() as db:
        service = PromptService(db)
        prompt = service.create_prompt(name=req.name, description=req.description)
        return PromptOut.model_validate(prompt)


@router.get("/{prompt_id}", response_model=PromptDetailOut)
def get_prompt(prompt_id: int):
    """Get a prompt and its metadata including latest version."""
    with SessionLocal() as db:
        service = PromptService(db)
        try:
            prompt = service.get_prompt(prompt_id)
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="prompt not found") from None

        # Get latest version if it exists
        latest_version = None
        versions, _, _, _ = service.get_prompt_versions(prompt_id, limit=1, offset=0)
        if versions:
            latest_version = PromptVersionOut.model_validate(versions[0])

        result = PromptDetailOut.model_validate(prompt)
        result.latest_version = latest_version
        return result


@router.patch("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, req: PromptUpdateRequest):
    """Update prompt metadata (name and/or description)."""
    with SessionLocal() as db:
        service = PromptService(db)
        try:
            prompt = service.update_prompt(
                prompt_id, name=req.name, description=req.description
            )
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="prompt not found") from None
        return PromptOut.model_validate(prompt)


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int):
    """Soft delete a prompt while retaining historical versions."""
    with SessionLocal() as db:
        service = PromptService(db)
        try:
            service.soft_delete_prompt(prompt_id)
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="prompt not found") from None
    return None


@router.get("/{prompt_id}/versions", response_model=PaginatedPromptVersionsOut)
def list_prompt_versions(prompt_id: int, limit: int = 50, offset: int = 0):
    """List all versions of a prompt."""
    with SessionLocal() as db:
        service = PromptService(db)
        try:
            rows, total, limit, offset = service.get_prompt_versions(
                prompt_id, limit=limit, offset=offset
            )
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="prompt not found") from None

        return PaginatedPromptVersionsOut(
            items=[PromptVersionOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.post("/{prompt_id}/versions", response_model=PromptVersionOut)
def append_prompt_version(prompt_id: int, req: PromptVersionCreateRequest):
    """Append a new version to a prompt."""
    with SessionLocal() as db:
        service = PromptService(db)
        try:
            version = service.append_version(
                prompt_id,
                model=req.model,
                template=req.template,
                parameters=req.parameters,
                created_by=req.created_by,
            )
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="prompt not found") from None

        return PromptVersionOut.model_validate(version)


@router.get("/{prompt_id}/versions/{version_id}", response_model=PromptVersionOut)
def get_prompt_version(prompt_id: int, version_id: int):
    """Get a specific version of a prompt."""
    with SessionLocal() as db:
        service = PromptService(db)
        try:
            version = service.get_prompt_version(prompt_id, version_id)
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="prompt not found") from None
        except PromptVersionNotFoundError:
            raise HTTPException(status_code=404, detail="version not found") from None

        return PromptVersionOut.model_validate(version)


@router.get("/works/{work_id}/prompts", response_model=PaginatedPromptsOut)
def list_work_prompts(work_id: int, q: str | None = Query(default=None), limit: int = 50, offset: int = 0):
    """List prompts available for a specific work."""
    with SessionLocal() as db:
        works_service = WorksService(db)
        prompt_service = PromptService(db)

        # Verify work exists
        try:
            works_service.get_work(work_id)
        except Exception:
            raise HTTPException(status_code=404, detail="work not found") from None

        rows, total, limit, offset = prompt_service.get_prompts_for_work(
            work_id, q=q, limit=limit, offset=offset
        )
        return PaginatedPromptsOut(
            items=[PromptOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/works/{work_id}/prompt", response_model=PromptDetailOut)
def get_work_prompt(work_id: int):
    """Get the prompt assigned to a work."""
    with SessionLocal() as db:
        works_service = WorksService(db)
        prompt_service = PromptService(db)

        # Verify work exists
        try:
            works_service.get_work(work_id)
        except Exception:
            raise HTTPException(status_code=404, detail="work not found") from None

        # Get work's prompt
        prompt = prompt_service.get_prompt_for_work(work_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="no prompt assigned to this work") from None

        # Get latest version if it exists
        latest_version = None
        versions, _, _, _ = prompt_service.get_prompt_versions(prompt.id, limit=1, offset=0)
        if versions:
            latest_version = PromptVersionOut.model_validate(versions[0])

        result = PromptDetailOut.model_validate(prompt)
        result.latest_version = latest_version
        return result


@router.patch("/works/{work_id}/prompt", response_model=PromptDetailOut)
def update_work_prompt(work_id: int, req: WorkPromptUpdateRequest):
    """Set or update the default prompt for a work."""
    with SessionLocal() as db:
        works_service = WorksService(db)
        prompt_service = PromptService(db)

        try:
            works_service.set_work_default_prompt(work_id, req.prompt_id)
        except Exception as exc:
            from services.exceptions import PromptNotFoundError, WorkNotFoundError

            if isinstance(exc, WorkNotFoundError):
                raise HTTPException(status_code=404, detail="work not found") from None
            if isinstance(exc, PromptNotFoundError):
                raise HTTPException(status_code=404, detail="prompt not found") from None
            raise

        # Get updated work's prompt
        prompt = prompt_service.get_prompt_for_work(work_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="prompt not found") from None

        # Get latest version if it exists
        latest_version = None
        versions, _, _, _ = prompt_service.get_prompt_versions(prompt.id, limit=1, offset=0)
        if versions:
            latest_version = PromptVersionOut.model_validate(versions[0])

        result = PromptDetailOut.model_validate(prompt)
        result.latest_version = latest_version
        return result
