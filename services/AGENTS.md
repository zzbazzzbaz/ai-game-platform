# Services
- `agent_server/`: Agent后端
- `api_server/`: 业务API
- `sandbox/`: Agent运行时沙箱镜像构建与发布
- `.env`: 唯一本地配置源
- `docker-compose-local.yml`: 本地编排
- `deploy/`: 仅生产(`docker-compose.yml`+`.env.example`)

## 规则

- 配置全读环境变量,禁写死,无默认值,缺失fail-fast
- 本地改必同步生产:`.env`→`deploy/.env.example`,`docker-compose-local.yml`→`deploy/docker-compose.yml`
- 跨服务契约（改动必须同步，见 `api_server/app/core/constants.py`、`agent_server/agent/core/constants.py`、`sandbox/build.py`）：
  - 沙箱命名 `game-{thread_id}`、标签 `aigame-thread`
  - 镜像名 `game-runner` + 环境变量 `MODAL_IMAGE_TAG`
  - 沙箱内路径：`/workspace/{work,input}`、`/skills`、`/opt/deps`
  - 发布接口 `POST /api/v1/internal/games/publish`；产物 key `games/{thread_id}/index.html`
- 沙箱资产（Phaser skills、工程骨架）只放 `sandbox/assets/`；运行期由 api_server 以命名镜像引用，不做运行时同步
- 沙箱内目录架构见 `sandbox/build.py` 顶部注释；变更须与两服务常量同步
