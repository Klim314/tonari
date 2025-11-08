from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = Field(default="tonari-backend")
    env: str = Field(default="dev")
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/tonari"
    )
    api_port: int = Field(default=8087)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

