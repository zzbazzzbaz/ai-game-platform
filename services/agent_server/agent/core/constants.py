from __future__ import annotations

from pathlib import Path

SKILL_SRC_PATH = Path(__file__).resolve().parent.parent / "skills" / "html5" / "SKILL.md"
SKILL_MOUNT_DIR = "/skills"
SKILL_MOUNT_PATH = f"{SKILL_MOUNT_DIR}/html5/SKILL.md"

SANDBOX_NAME_PREFIX = "game-"
SANDBOX_TAG_THREAD = "aigame-thread"

AUTH_VERIFY_TIMEOUT_SECONDS = 10
SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS = 30 * 60
