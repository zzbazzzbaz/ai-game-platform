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

# langgraph.json 的 graphs 按「模块:函数名」注册本模块的 build_*_agent，graph id 保持 single_player。
# 必须是工厂函数而非模块级图变量：沙箱与 publish_game 工具都绑定会话（thread_id），
# 而 thread_id 只存在于 config，只能在每次请求时构造图。


def _require_thread_id(config: RunnableConfig) -> str:
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    return thread_id


async def build_single_player_agent(config: RunnableConfig) -> Any:
    thread_id = _require_thread_id(config)
    settings = get_settings()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    publish_tool: Callable = make_publish_game_tool(
        thread_id=thread_id,
        api_internal_url=settings.api_internal_url,
        internal_token=settings.auth_internal_token,
    )
    return create_deep_agent(
        model=get_llm(),
        system_prompt=SINGLE_PLAYER_PROMPT,
        skills=[SKILL_MOUNT_DIR],
        tools=[publish_tool],
        backend=ModalBackend(sandbox=sandbox),
    )


async def build_multiplayer_agent(config: RunnableConfig) -> Any:
    # 沙箱模板（独立 WORK_ROOT）与提示词均未落地，本期不注册进 langgraph.json
    raise NotImplementedError("多人模式尚未实现")
