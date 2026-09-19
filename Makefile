.PHONY: up down install run-api run-agent run-web

up:
	docker compose -f services/docker-compose-local.yml up -d

down:
	docker compose -f services/docker-compose-local.yml down

install:
	cd services/api_server && uv sync --frozen
	cd services/agent_server && uv sync --frozen
	cd docs/test-frontend && npm install

run-api:
	set -a && . services/.env && POSTGRES_HOST=localhost uv run --frozen --directory services/api_server fastapi run --port 8000 --workers 1

run-agent:
	cd services/agent_server && API_INTERNAL_URL=http://localhost:8000 uv run --frozen langgraph dev --no-reload

run-web:
	cd docs/test-frontend && npm run dev
