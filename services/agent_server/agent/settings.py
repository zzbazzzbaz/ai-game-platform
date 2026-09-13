from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    LLM_PROVIDER: Literal["deepseek", "openai"]
    LLM_MODEL_ID: str
    LLM_BASE_URL: str
    LLM_API_KEY: str
    MODAL_TOKEN_ID: str
    MODAL_TOKEN_SECRET: str
    MODAL_APP: str
    LANGSMITH_API_KEY: str
    LANGSMITH_TRACING: bool
    LANGSMITH_PROJECT: str
    API_INTERNAL_URL: str
    AUTH_INTERNAL_TOKEN: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
