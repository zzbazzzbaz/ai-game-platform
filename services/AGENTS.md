# Services
- `agent_server/`: Agent后端
- `api_server/`: 业务API
- `.env`: 唯一本地配置源
- `docker-compose-local.yml`: 本地编排
- `deploy/`: 仅生产(`docker-compose.yml`+`.env.example`)

## 规则

- 配置全读环境变量,禁写死,无默认值,缺失fail-fast
- 本地改必同步生产:`.env`→`deploy/.env.example`,`docker-compose-local.yml`→`deploy/docker-compose.yml`
- 跨服务契约（两服务各留一份常量，改动必须同步）：沙箱命名 `game-{thread_id}`、标签 `aigame-thread`、工作区路径 `/workspace/{work,input}`；见 `api_server/app/core/constants.py` 与 `agent_server/agent/core/constants.py`