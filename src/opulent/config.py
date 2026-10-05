from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Opulent"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BASE_URL: str = "http://localhost:8000"

    # Default to sqlite for quick testing/local dev if no Postgres configured,
    # but Postgres in Docker / production
    DATABASE_URL: str = "postgresql+asyncpg://opulent:opulent@localhost:5432/opulent"

    PAGE_SIZE_DEFAULT: int = 15
    PAGE_SIZE_MAX: int = 100
    MAX_CONTENT_LENGTH: int = 1_000_000  # 1MB limit for document content


@lru_cache
def get_settings() -> Settings:
    return Settings()
