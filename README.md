# AI 游戏平台（MVP）

自然语言对话生成单文件 HTML5 游戏：左对话、右试玩，多轮迭代。

## 本地启动

```bash
docker compose -f services/docker-compose-local.yml up -d

cd services/agent_server && uv run --frozen langgraph dev --no-reload

cd services/api_server && set -a && . ../.env && POSTGRES_HOST=localhost REDIS_HOST=localhost uv run --frozen uvicorn app.main:app --port 8000 --workers 1

cd docs/test-frontend && npm install && npm run dev
```

打开 http://localhost:3000：登录 → 新会话 → 对话 → 审批 → 生成 → 发布 → 试玩。

## 结构

- `services/agent_server/`：DeepAgent 运行时（LangGraph Server）
- `services/api_server/`：业务 API（会话/发布/试玩代理）
- `docs/test-frontend/`：联调测试桩（正式前端在 `frontend/`，他人负责）
- `docs/chat/`：过程文档（不进 git）
