import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents.translation_agent import TranslationAgent
from app.config import settings
from app.schemas import LabStreamRequest
from constants.llm import get_model_info
from observability import TraceContext

router = APIRouter()


@router.post("/stream")
async def stream_lab_translation(req: LabStreamRequest):
    """
    Stream translation for the prompt lab.
    This endpoint is ephemeral and does not save to the database.
    """
    # 1. Resolve Model & Provider
    model_info = get_model_info(req.model)
    if not model_info:
        # Fallback or error? For now, error if model not found in our constants
        # But maybe we allow raw strings if the user knows what they are doing?
        # Safest is to rely on our supported list.
        # Check if it matches a known ID even if get_model_info fails?
        # constants.llm.get_model_info handles looking up by ID.
        raise HTTPException(status_code=400, detail=f"Unsupported model: {req.model}")

    provider = model_info.provider
    api_key = settings.get_api_key_for_provider(provider)

    # 2. Instantiate Agent Dynamically
    # We use a context_window of 0 because this is a stateless "snippet" translation
    # (unless we later add a feature to provide context, but MVP is raw text).
    agent = TranslationAgent(
        model=req.model,
        api_key=api_key,
        api_base=settings.translation_api_base_url,
        chunk_chars=settings.translation_chunk_chars,
        context_window=0,  # Stateless
        system_prompt=req.template,
        provider=provider,
    )

    trace = TraceContext(
        name="lab.stream",
        session_id=f"lab:{uuid.uuid4()}",
        metadata={
            "model": req.model,
            "provider": provider,
            "template_len": len(req.template),
            "text_len": len(req.text),
        },
        tags=["lab", provider],
    )

    # 3. Stream Response
    async def event_generator():
        try:
            async for chunk in agent.stream_segment(req.text, trace=trace):
                # Raw character streaming for simple frontend consumption
                yield chunk
        except Exception as e:
            # yield f"error: {str(e)}"
            raise e

    return StreamingResponse(event_generator(), media_type="text/plain")
