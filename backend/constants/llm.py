"""Supported LLM models for translations."""

from dataclasses import dataclass
from typing import List


@dataclass
class ModelInfo:
    """Information about a supported LLM model."""

    id: str  # Model identifier (e.g., "gpt-4o", "gpt-5")
    name: str  # Display name (e.g., "GPT-4o", "GPT-5")
    provider: str  # Provider (e.g., "openai")
    max_tokens: int  # Maximum context window
    supports_streaming: bool = True  # Whether model supports streaming
    cost_per_1m_input: float = 0.0  # Cost per 1M input tokens in USD
    cost_per_1m_output: float = 0.0  # Cost per 1M output tokens in USD


# GPT-5 Series (Latest flagship models)
GPT_5 = ModelInfo(
    id="gpt-5",
    name="GPT-5",
    provider="openai",
    max_tokens=128000,
    cost_per_1m_input=1.25,
    cost_per_1m_output=10,
)

GPT_5_MINI = ModelInfo(
    id="gpt-5-mini",
    name="GPT-5 Mini",
    provider="openai",
    max_tokens=128000,
    cost_per_1m_input=0.25,
    cost_per_1m_output=1.0,
)

GPT_5_NANO = ModelInfo(
    id="gpt-5-nano",
    name="GPT-5 Nano",
    provider="openai",
    max_tokens=128000,
    cost_per_1m_input=0.05,
    cost_per_1m_output=0.40,
)

# GPT-4 Series
GPT_4O = ModelInfo(
    id="gpt-4o",
    name="GPT-4o",
    provider="openai",
    max_tokens=128000,
    cost_per_1m_input=2.50,
    cost_per_1m_output=10.00,
)

GPT_4O_MINI = ModelInfo(
    id="gpt-4o-mini",
    name="GPT-4o Mini",
    provider="openai",
    max_tokens=128000,
    cost_per_1m_input=0.15,
    cost_per_1m_output=0.60,
)

GPT_4_TURBO = ModelInfo(
    id="gpt-4-turbo",
    name="GPT-4 Turbo",
    provider="openai",
    max_tokens=128000,
    cost_per_1m_input=10.00,
    cost_per_1m_output=30.00,
)

GPT_4 = ModelInfo(
    id="gpt-4",
    name="GPT-4",
    provider="openai",
    max_tokens=8192,
    cost_per_1m_input=30.00,
    cost_per_1m_output=60.00,
)

# GPT-3.5 Series
GPT_3_5_TURBO = ModelInfo(
    id="gpt-3.5-turbo",
    name="GPT-3.5 Turbo",
    provider="openai",
    max_tokens=16384,
    cost_per_1m_input=0.50,
    cost_per_1m_output=1.50,
)

# All available models
AVAILABLE_MODELS: List[ModelInfo] = [
    # OpenAI mainline text models (newest first)
    GPT_5,
    GPT_5_MINI,
    GPT_5_NANO,
    GPT_4O,
    GPT_4O_MINI,
    GPT_4_TURBO,
    GPT_4,
    GPT_3_5_TURBO,
]

# Model lookup by ID
MODEL_BY_ID = {model.id: model for model in AVAILABLE_MODELS}


def get_model_info(model_id: str) -> ModelInfo | None:
    """Get model information by ID."""
    return MODEL_BY_ID.get(model_id)


def list_models_by_provider(provider: str) -> List[ModelInfo]:
    """Get all models from a specific provider."""
    return [m for m in AVAILABLE_MODELS if m.provider == provider]
