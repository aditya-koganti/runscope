.PHONY: setup dev stop clean test test-backend test-frontend test-e2e lint format security migrate seed demo logs load-test load-test-mutations kubernetes-render

setup:
	python -m pip install -e ".[dev]"
	cd apps/web && npm ci

dev:
	docker compose up --build

stop:
	docker compose down

clean:
	docker compose down --volumes --remove-orphans

test: test-backend test-frontend

test-backend:
	python -m pytest

test-frontend:
	cd apps/web && npm test

test-e2e:
	cd apps/web && npm run e2e

lint:
	python -m ruff check .
	python -m mypy
	cd apps/web && npm run lint && npm run typecheck

format:
	python -m ruff format .
	cd apps/web && npx prettier --write .

security:
	python -m pip_audit
	cd apps/web && npm audit --audit-level=high

migrate:
	alembic -c services/api/alembic.ini upgrade head

seed:
	python -m runscope_api.cli seed

demo:
	python scripts/demo.py

logs:
	docker compose logs --follow --tail=200

load-test:
	locust -f tests/load/locustfile.py --host http://localhost:8000/api/v1 --headless --users 5 --spawn-rate 1 --run-time 30s --tags read sse

load-test-mutations:
	RUNSCOPE_LOAD_ENABLE_MUTATIONS=true locust -f tests/load/locustfile.py --host http://localhost:8000/api/v1 --headless --users 2 --spawn-rate 1 --run-time 20s --tags submission scheduler

kubernetes-render:
	kubectl kustomize infra/kubernetes
