import asyncio

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig

from agent.infra.modal_backend import ModalBackend
from agent.infra.modal_sandbox import attach_thread_sandbox
from agent.infra.model import get_main_model
from agent.infra.skill_sync import SKILL_MOUNT_DIR, sync_skill
from agent.prompts.game_designer import SYSTEM_PROMPT
from agent.tools.design import submit_game_design


async def graph(config: RunnableConfig):
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("缺少 thread_id：请先调 api /sessions/ensure 创建会话再连接 agent")
    model = get_main_model()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    await asyncio.to_thread(sync_skill, sandbox)
    return create_deep_agent(
        model=model,
        tools=[submit_game_design],
        system_prompt=SYSTEM_PROMPT,
        skills=[SKILL_MOUNT_DIR],
        backend=ModalBackend(sandbox=sandbox),
        interrupt_on={"submit_game_design": {"allowed_decisions": ["approve", "edit", "reject"]}},
    )
