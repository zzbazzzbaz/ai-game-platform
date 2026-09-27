# services/sandbox —— 沙箱镜像构建

构建并发布沙箱镜像 `game-runner`。镜像是**平台资产**：工具链 + Phaser 技能库 + 单人游戏工程骨架全部烘焙在内。运行时由 `api_server` 以 `Image.from_name("game-runner:<tag>")` 引用，本目录不被任何服务在运行期 import。

## 内容

```
assets/
├── skills/                         # Phaser 技能库（deepagents 从沙箱 /skills 读取）
└── templates/single-player/        # 单人游戏工程骨架（Node 工程 + 门禁 + 构建脚本）
```

镜像布局：

```
/skills/                            # 技能库
/opt/deps/                          # npm ci 安装的可复现依赖
/workspace/input/                   # 空目录：用户素材（只读）
/workspace/work/                    # 工程骨架，唯一可写区
└── node_modules -> /opt/deps/node_modules   # 软链，快照时被 _walk 跳过
```

## 构建

```bash
# 开发者本机（读取 services/.env 的 Modal 凭证）
make sandbox-image                 # 等价于下条，默认 tag latest
make sandbox-image SANDBOX_TAG=20260927

# 直接调用
cd services/sandbox
uv run python build.py --tag latest --tag "$(git rev-parse --short HEAD)"
```

CI（`.github/workflows/sandbox-image.yml`）在 `services/sandbox/**` 变更时自动发布 `latest` 与 `<git-sha>` 两个 tag。

## 约定

- **改 skill/骨架 → 重建镜像 → 新建沙箱才生效**（镜像冻结资产）。
- 骨架里的 `package.json` / `package-lock.json` 是依赖层输入，改动会触发 `npm ci` 层重建；其余骨架文件在更后的层，重建更便宜。
- 镜像是 linux/amd64；本地/CI 均为 amd64 环境。
