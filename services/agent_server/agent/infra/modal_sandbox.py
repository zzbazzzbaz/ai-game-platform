import modal
from modal.exception import NotFoundError

from agent.settings import get_settings

SANDBOX_NAME_PREFIX = "game-"
SANDBOX_TAG_THREAD = "aigame-thread"


def sandbox_name(thread_id: str) -> str:
    return f"{SANDBOX_NAME_PREFIX}{thread_id}"


def sandbox_tags(thread_id: str) -> dict[str, str]:
    return {SANDBOX_TAG_THREAD: thread_id}


def attach_thread_sandbox(thread_id: str) -> modal.Sandbox:
    try:
        return modal.Sandbox.from_name(get_settings().MODAL_APP, sandbox_name(thread_id))
    except NotFoundError:
        raise RuntimeError("会话环境已过期，请重新创建会话后再继续") from None
