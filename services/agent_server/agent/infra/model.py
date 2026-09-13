from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent.settings import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    if settings.LLM_PROVIDER not in ("deepseek", "openai"):
        raise ValueError(f"不支持的 LLM_PROVIDER：{settings.LLM_PROVIDER}，仅支持 deepseek/openai")
    return init_chat_model(
        settings.LLM_MODEL_ID,
        model_provider=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )
