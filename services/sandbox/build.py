"""构建并发布沙箱镜像 game-runner。

镜像内容：Node LTS + Playwright/Chromium + Phaser 技能库 + 单人游戏工程骨架。
运行期由 api_server 以 Image.from_name("game-runner:<tag>") 引用。

用法：
    uv run python build.py --tag latest --tag "$(git rev-parse --short HEAD)"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SKILLS_DIR = ASSETS / "skills"
TEMPLATE_DIR = ASSETS / "templates" / "single-player"

IMAGE_NAME = "game-runner"
BUILDER_APP_NAME = "game-runner-builder"
BASE_IMAGE = "node:22-bookworm-slim"

SKILLS_MOUNT = "/skills"
DEPS_ROOT = "/opt/deps"
WORK_ROOT = "/workspace/work"
INPUT_ROOT = "/workspace/input"

# 这些是本地/运行时产物，不进镜像
_IGNORED_NAMES = frozenset({"node_modules", "dist", ".runtime"})


def _ignore(path: Path) -> bool:
    return path.name in _IGNORED_NAMES


def build_image() -> modal.Image:
    return (
        modal.Image.from_registry(BASE_IMAGE)
        # 依赖层：只依赖 package.json / package-lock.json，改其它骨架文件不会触发重建
        .add_local_file(TEMPLATE_DIR / "package.json", f"{DEPS_ROOT}/package.json", copy=True)
        .add_local_file(
            TEMPLATE_DIR / "package-lock.json", f"{DEPS_ROOT}/package-lock.json", copy=True
        )
        .run_commands(f"cd {DEPS_ROOT} && npm ci --no-audit --no-fund")
        .run_commands(f"cd {DEPS_ROOT} && npx playwright install --with-deps chromium")
        # 资产层：技能库 + 工程骨架（最后，便于小改快速重建）
        .add_local_dir(SKILLS_DIR, SKILLS_MOUNT, copy=True)
        .add_local_dir(TEMPLATE_DIR, WORK_ROOT, copy=True, ignore=_ignore)
        .run_commands(
            f"mkdir -p {INPUT_ROOT}",
            f"ln -s {DEPS_ROOT}/node_modules {WORK_ROOT}/node_modules",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and publish the game-runner sandbox image")
    parser.add_argument(
        "--tag",
        action="append",
        required=True,
        help="镜像 tag，可重复传入（如 --tag latest --tag <sha>）",
    )
    args = parser.parse_args()

    app = modal.App.lookup(BUILDER_APP_NAME, create_if_missing=True)
    image = build_image()
    with modal.enable_output():
        image.build(app)
    for tag in args.tag:
        image.publish(f"{IMAGE_NAME}:{tag}")
        print(f"published {IMAGE_NAME}:{tag}")


if __name__ == "__main__":
    main()
