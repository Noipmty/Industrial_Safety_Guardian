.PHONY: dev dev-backend dev-frontend infra-up infra-down infra-logs migrate migrate-new test test-frontend lint eval install-backend install-frontend generate-types

dev:
	cd infra && docker compose up -d
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev &

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

infra-up:
	cd infra && docker compose up -d

infra-down:
	cd infra && docker compose down

infra-logs:
	cd infra && docker compose logs -f

migrate:
	cd backend && uv run alembic upgrade head

migrate-new:
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

test:
	cd backend && uv run pytest -v

test-frontend:
	cd frontend && npm run test

lint:
	cd backend && uv run ruff check . && uv run basedpyright

eval:
	cd eval && python run_ragas.py

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

generate-types:
	cd frontend && npx openapi-typescript ./openapi.json -o ./src/api/types.ts
