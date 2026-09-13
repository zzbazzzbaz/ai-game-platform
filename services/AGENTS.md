# Services
- `agent_server/`: Agent后端
- `api_server/`: 业务API
- `.env.local`: 唯一本地配置源
- `docker-compose-local.yml`: 本地编排
- `deploy/`: 仅生产(`docker-compose.yml`+`.env.example`)

## 规则

- 配置全读环境变量,禁写死,无默认值,缺失fail-fast
- 本地改必同步生产:`.env.local`→`deploy/.env.example`,`docker-compose-local.yml`→`deploy/docker-compose.yml`