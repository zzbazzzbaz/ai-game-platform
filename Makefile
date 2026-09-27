.PHONY: up down install run-api run-agent run-web

ENV_FILE := $(CURDIR)/services/.env

up:
	docker compose -f services/docker-compose-local.yml up -d

down:
	docker compose -f services/docker-compose-local.yml down

install:
	cd services/api_server && uv sync --frozen
	cd services/agent_server && uv sync --frozen
	cd services/sandbox && uv sync --frozen
	cd docs/test-frontend && npm install

# 服务跑在宿主机、PG 跑在容器，端口已发布，故覆盖容器主机名
run-api:
	POSTGRES_HOST=localhost uv run --frozen --directory services/api_server --env-file $(ENV_FILE) fastapi run --port 8000 --workers 1

run-agent:
	uv run --frozen --directory services/agent_server --env-file $(ENV_FILE) langgraph dev --no-reload

run-web:
	cd docs/test-frontend && npm run dev
