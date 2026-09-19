import modal
from modal.exception import SandboxFilesystemNotFoundError

from agent.core.constants import SKILL_MOUNT_PATH, SKILL_SRC_PATH


def _read_remote(path: str, sandbox: modal.Sandbox) -> bytes | None:
    try:
        return bytes(sandbox.filesystem.read_bytes(path))
    except FileNotFoundError, SandboxFilesystemNotFoundError:
        return None


def sync_skill(sandbox: modal.Sandbox) -> None:
    want = SKILL_SRC_PATH.read_bytes()
    if _read_remote(SKILL_MOUNT_PATH, sandbox) != want:
        sandbox.filesystem.write_bytes(want, SKILL_MOUNT_PATH)
