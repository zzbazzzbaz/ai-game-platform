from __future__ import annotations

from pathlib import Path

SKILL_SRC_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILL_MOUNT_DIR = "/skills"

SANDBOX_NAME_PREFIX = "game-"
SANDBOX_TAG_THREAD = "aigame-thread"

AUTH_VERIFY_TIMEOUT_SECONDS = 10
SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS = 30 * 60
