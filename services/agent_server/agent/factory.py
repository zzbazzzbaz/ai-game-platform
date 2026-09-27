import asyncio
from collections.abc import Callable
from typing import Any

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig

from agent.core.config import get_settings
from agent.core.constants import SKILL_MOUNT_DIR
from agent.infra.modal_backend import ModalBackend
from agent.infra.modal_sandbox import attach_thread_sandbox
from agent.infra.model import get_llm
from agent.prompts.single_player import SYSTEM_PROMPT as SINGLE_PLAYER_PROMPT
from agent.tools.publish_game import make_publish_game_tool

# 单/多 agent 按 mode 区分：本期只实现 single_player，multiplayer 预留
MODE_PROMPTS: dict[str, str] = {
    "single_player": SINGLE_PLAYER_PROMPT,
}


def _require_thread_id(config: RunnableConfig) -> str:
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    return thread_id


async def build_agent(mode: str, config: RunnableConfig) -> Any:
    prompt = MODE_PROMPTS.get(mode)
    if prompt is None:
        raise RuntimeError(f"未知游戏模式：{mode}")
    thread_id = _require_thread_id(config)
    settings = get_settings()
    model = get_llm()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    publish_tool: Callable = make_publish_game_tool(
        thread_id=thread_id,
        api_internal_url=settings.api_internal_url,
        internal_token=settings.auth_internal_token,
    )
    return create_deep_agent(
        model=model,
        system_prompt=prompt,
        skills=[SKILL_MOUNT_DIR],
        tools=[publish_tool],
        backend=ModalBackend(sandbox=sandbox),
    )
