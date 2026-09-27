import asyncio

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig

from agent.core.config import get_settings
from agent.core.constants import SKILL_MOUNT_DIR
from agent.infra.modal_backend import ModalBackend
from agent.infra.modal_sandbox import attach_thread_sandbox
from agent.infra.model import get_llm
from agent.prompts.game_designer import SYSTEM_PROMPT
from agent.tools.publish_game import make_publish_game_tool


async def graph(config: RunnableConfig):
    configurable = config.get("configurable") or {}
    thread_id = configurable.get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    settings = get_settings()
    model = get_llm()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    publish_tool = make_publish_game_tool(
        thread_id=thread_id,
        api_internal_url=settings.api_internal_url,
        internal_token=settings.auth_internal_token,
    )
    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        skills=[SKILL_MOUNT_DIR],
        tools=[publish_tool],
        backend=ModalBackend(sandbox=sandbox),
    )
