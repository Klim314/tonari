from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="tonari-backend")
    env: str = Field(default="dev")
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/tonari"
    )
    api_port: int = Field(default=8087)
    # Legacy field for backward compatibility (OpenAI key)
    translation_api_key: str | None = Field(default=None)
    # Provider-specific API keys
    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    translation_model: str = Field(default="gpt-5.2")
    translation_api_base_url: str | None = Field(default=None)
    translation_chunk_chars: int = Field(default=160)
    translation_context_segments: int = Field(default=3)
    prompt_override_secret: str = Field(default="tonari-prompt-override-secret")
    prompt_override_token_ttl_seconds: int = Field(default=600)

    def get_api_key_for_provider(self, provider: str) -> str | None:
        """Get the appropriate API key for a given provider."""
        if provider == "openai":
            return self.openai_api_key or self.translation_api_key
        elif provider == "gemini":
            return self.gemini_api_key
        return None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
