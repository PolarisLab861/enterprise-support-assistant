from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Support Assistant"
    environment: str = "development"
    database_url: str = "sqlite:///./support_assistant.db"
    dify_base_url: str = "http://localhost/v1"
    dify_api_key: str = ""
    dify_workflow_id: str = ""
    dify_timeout_seconds: float = 30
    mock_ai: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
