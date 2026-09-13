from pathlib import Path

import modal
from modal.exception import SandboxFilesystemNotFoundError

SKILL_SRC = Path(__file__).resolve().parent.parent / "skills" / "html5" / "SKILL.md"
SKILL_MOUNT_DIR = "/skills"
SKILL_MOUNT_PATH = "/skills/html5/SKILL.md"


def _read_remote(path: str, sandbox: modal.Sandbox) -> bytes | None:
    try:
        return bytes(sandbox.filesystem.read_bytes(path))
    except FileNotFoundError, SandboxFilesystemNotFoundError:
        return None


def sync_skill(sandbox: modal.Sandbox) -> None:
    want = SKILL_SRC.read_bytes()
    if _read_remote(SKILL_MOUNT_PATH, sandbox) != want:
        sandbox.filesystem.write_bytes(want, SKILL_MOUNT_PATH)
