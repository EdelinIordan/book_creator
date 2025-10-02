.PHONY: install lint lint-python lint-js test docker-up docker-down format setup

install:
	pip install -r apps/api/requirements-dev.txt
	pip install -e libs/python[providers]
	npm --prefix apps/frontend install

lint: lint-python lint-js

lint-python:
	ruff check apps services

lint-js:
	npm --prefix apps/frontend run lint || true

test:
	@if [ -x .venv/bin/python ]; then \
		PYTHONPATH="$(PWD):$(PWD)/libs/python" .venv/bin/python -m pytest tests; \
	else \
		PYTHONPATH="$(PWD):$(PWD)/libs/python" python3 -m pytest tests; \
	fi

format:
	ruff format apps services
	npm --prefix apps/frontend run lint -- --fix || true

setup:
	cp -n .env.example .env || true

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v
