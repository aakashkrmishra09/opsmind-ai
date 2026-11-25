from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "OpsMind AI"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    simulation_mode: bool = True

    jwt_secret_key: str = "change-me-in-local-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str = (
        "postgresql+asyncpg://opsmind:opsmind_dev_password@localhost:5432/opsmind"
    )
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "fallback"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    embedding_provider: str = "fallback"
    embedding_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()