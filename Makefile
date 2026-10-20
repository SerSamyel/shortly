# Run `make help` for the list. On Windows use Git Bash, WSL, or the commands in README.md.
.PHONY: help install up down logs deps-up deps-down dev-backend dev-consumer dev-frontend dev-mock \
        test test-backend test-frontend test-integration test-all lint geoip

TEST_DB ?= postgresql+asyncpg://shortly:shortly@localhost:5432/shortly_test
TEST_REDIS ?= redis://localhost:6379/15

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	cd backend && uv sync
	cd frontend && npm install

up: ## Build and run the whole stack on http://localhost:8000
	docker compose up --build

down: ## Stop the stack (data volume is kept)
	docker compose down

logs: ## Follow app and consumer logs
	docker compose logs -f app consumer

deps-up: ## Start only Postgres, Redis and Redpanda (for local dev and integration tests)
	docker compose up -d --wait postgres redis redpanda

deps-down:
	docker compose stop postgres redis redpanda

DEV_ENV = DATABASE_URL=postgresql://shortly:shortly@localhost:5432/shortly \
	REDIS_URL=redis://localhost:6379/0 KAFKA_BOOTSTRAP=localhost:19092

dev-backend: ## Run the API with reload against the deps from `make deps-up`
	cd backend && $(DEV_ENV) uv run alembic upgrade head && \
		$(DEV_ENV) uv run uvicorn shortly.app:create_app --factory --reload

dev-consumer: ## Run the click consumer against the deps from `make deps-up`
	cd backend && $(DEV_ENV) uv run shortly-consumer

dev-frontend: ## Run the SPA on http://localhost:5173 against the local API
	cd frontend && npm run dev

dev-mock: ## Run the SPA with the in-memory mock backend (no server needed)
	cd frontend && npm run dev:mock

test: test-backend test-frontend ## Unit tests: backend + frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

test-integration: ## Integration tests (run `make deps-up` first)
	cd backend && TEST_DATABASE_URL=$(TEST_DB) TEST_REDIS_URL=$(TEST_REDIS) \
		TEST_KAFKA_BOOTSTRAP=localhost:19092 uv run pytest tests_integration -v

test-all: test test-integration ## Everything

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npx tsc -b

geoip: ## Download the free DB-IP Lite country database into geoip/
	./scripts/download-geoip.sh
