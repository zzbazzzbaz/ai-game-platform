import asyncio

from deepagents import create_deep_agent
from langchain.agents.middleware import InterruptOnConfig
from langchain_core.runnables import RunnableConfig

from agent.infra.modal_backend import ModalBackend
from agent.infra.modal_sandbox import attach_thread_sandbox
from agent.infra.model import get_main_model
from agent.infra.skill_sync import SKILL_MOUNT_DIR, sync_skill
from agent.prompts.game_designer import SYSTEM_PROMPT
from agent.tools.design import submit_game_design


DESIGN_INTERRUPT_ON: dict[str, InterruptOnConfig] = {
    "submit_game_design": {"allowed_decisions": ["approve", "edit", "reject"]}
}


async def graph(config: RunnableConfig):
    thread_id = (config.get("configurable") or {}).get("thread_id")
    if not thread_id or not isinstance(thread_id, str):
        raise RuntimeError("会话尚未创建，请先创建新会话再开始对话")
    model = get_main_model()
    sandbox = await asyncio.to_thread(attach_thread_sandbox, thread_id)
    await asyncio.to_thread(sync_skill, sandbox)
    return create_deep_agent(
        model=model,
        tools=[submit_game_design],
        system_prompt=SYSTEM_PROMPT,
        skills=[SKILL_MOUNT_DIR],
        backend=ModalBackend(sandbox=sandbox),
        interrupt_on=DESIGN_INTERRUPT_ON,
    )
