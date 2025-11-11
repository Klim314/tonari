from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="tonari-backend")
    env: str = Field(default="dev")
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/tonari"
    )
    api_port: int = Field(default=8087)
    translation_api_key: str | None = Field(default=None)
    translation_model: str = Field(default="gpt-4o-mini")
    translation_api_base_url: str | None = Field(default=None)
    translation_chunk_chars: int = Field(default=160)
    translation_context_segments: int = Field(default=3)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
