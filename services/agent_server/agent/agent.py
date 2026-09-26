import asyncio

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig

from agent.core.constants import SKILL_MOUNT_DIR
from agent.infra.modal_backend import ModalBackend
from agent.infra.modal_sandbox import attach_thread_sandbox
from agent.infra.model import get_llm
from agent.infra.skill_sync import sync_skill
from agent.prompts.game_designer import SYSTEM_PROMPT


async def graph(config: RunnableConfig):
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    model = get_llm()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    await asyncio.to_thread(sync_skill, sandbox)
    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        skills=[SKILL_MOUNT_DIR],
        backend=ModalBackend(sandbox=sandbox),
    )
