from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import LabStreamRequest
from agents.translation_agent import TranslationAgent
from constants.llm import get_model_info

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
        api_base=settings.translation_api_base_url, # Usually same base URL for same provider, but strictly this might need per-provider URLs if using different proxies. 
        # For now, assuming settings.translation_api_base_url is generic or ignored by SDKs that pick up env vars.
        # Actually TranslationAgent passes this to BaseAgent.
        chunk_chars=settings.translation_chunk_chars,
        context_window=0, # Stateless
        system_prompt=req.template,
        provider=provider,
    )

    # 3. Stream Response
    async def event_generator():
        try:
            async for chunk in agent.stream_segment(req.text):
                # SSE format: "data: <content>\n\n"
                # We replace newlines in data to avoid breaking SSE protocol if using standard library, 
                # but raw chunk usually is just text. 
                # Standardization: often we send JSON in data like data: {"text": "..."} 
                # but for simple text streaming, just raw text is often used. 
                # Let's use JSON to be safe and extensible.
                # data = json.dumps({"text": chunk})
                # yield f"data: {data}\n\n"
                
                # Correction: The existing implementation might just want raw text or specific format.
                # But typically SSE expects "data: ...\n\n". 
                # If we just yield raw text, it's a "StreamingResponse" but not technically SSE unless media_type="text/event-stream".
                # If media_type is generic, browsers handle it as a long download.
                # Implementation Plan said "Server-Sent Events".
                
                # Let's output raw characters for now, as that's easiest for a simple "read stream" on frontend,
                # unless we want structured events.
                yield chunk
        except Exception as e:
            # yield f"error: {str(e)}"
            raise e

    return StreamingResponse(event_generator(), media_type="text/plain")
