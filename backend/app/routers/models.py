"""Router for LLM model information."""

from fastapi import APIRouter

from app.schemas import ModelInfoOut, ModelsListOut
from constants.llm import AVAILABLE_MODELS

router = APIRouter()


@router.get("/", response_model=ModelsListOut)
def list_models():
    """List all available LLM models for translations."""
    model_items = [
        ModelInfoOut(
            id=model.id,
            name=model.name,
            provider=model.provider,
            max_tokens=model.max_tokens,
            supports_streaming=model.supports_streaming,
            cost_per_1m_input=model.cost_per_1m_input,
            cost_per_1m_output=model.cost_per_1m_output,
        )
        for model in AVAILABLE_MODELS
    ]
    return ModelsListOut(items=model_items, total=len(model_items))
