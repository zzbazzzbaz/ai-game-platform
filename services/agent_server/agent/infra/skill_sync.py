import modal
from modal.exception import SandboxFilesystemError

from agent.core.constants import SKILL_MOUNT_DIR, SKILL_SRC_DIR

_MISSING = (FileNotFoundError, SandboxFilesystemError)


def _read_remote(path: str, sandbox: modal.Sandbox) -> bytes | None:
    try:
        return bytes(sandbox.filesystem.read_bytes(path))
    except _MISSING:
        return None


def _local_files() -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for path in sorted(SKILL_SRC_DIR.rglob("*")):
        if path.is_file():
            rel = path.relative_to(SKILL_SRC_DIR).as_posix()
            files.append((f"{SKILL_MOUNT_DIR}/{rel}", path.read_bytes()))
    return files


def sync_skills(sandbox: modal.Sandbox) -> None:
    """把本地 agent/skills/** 全量同步到沙箱 /skills/**，逐文件比对字节。"""
    for remote_path, content in _local_files():
        if _read_remote(remote_path, sandbox) != content:
            sandbox.filesystem.write_bytes(content, remote_path)
