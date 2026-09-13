# Services 目录约定

## 1. 目录结构与职责

| 路径（相对 `services/`） | 类型 | 职责说明 |
|---|---|---|
| `agent_server/` | Agent 后端 | 基于 LangGraph 的智能体服务。本地开发用 `langgraph dev` 启动，生产用 `langgraph up` 启动。 |
| `api_server/` | 业务后端 | 业务逻辑 API 服务（非 Agent 逻辑放这里）。 |
| `.env.local` | 本地配置 | 本地开发全部配置写这里，是唯一本地配置源。 |
| `docker-compose-local.yml` | 本地编排 | 本地开发用 Docker Compose 文件。 |
| `deploy/` | 生产部署目录 | 只放生产部署相关文件，禁止放开发脚本。 |
| `deploy/docker-compose.yml` | 生产编排 | 生产环境 Docker Compose 文件。 |
| `deploy/.env.example` | 生产配置模板 | 生产环境密钥/变量模板 |

## 2. 配置管理（MUST）

1. 本地配置唯一入口是 `services/.env.local`。
2. `agent_server/` 和 `api_server/` 内的 `config / settings` 模块：
   - MUST 从环境变量读取。
   - MUST NOT 设置默认值。
   - 若 `.env` 未配置对应项，MUST 直接报错启动失败（fail-fast），禁止静默降级。
3. 禁止在代码里 hardcode 本地/生产地址、密钥、端口。

#### 2.1 本地与生产同步规则

修改本地文件后，必须手动同步生产对应文件：

| 修改本地文件 | 必须同步到 |
|---|---|
| `services/.env.local` | `services/deploy/.env.example` |
| `services/docker-compose-local.yml` | `services/deploy/docker-compose.yml` |