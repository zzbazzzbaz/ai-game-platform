from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from agent.settings import get_settings


@lru_cache
def get_main_model() -> BaseChatModel:
    settings = get_settings()
    if settings.LLM_PROVIDER == "deepseek":
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    if settings.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    raise ValueError(f"不支持的 LLM_PROVIDER：{settings.LLM_PROVIDER}，仅支持 deepseek/openai")
