.PHONY: install install-all dev test test-cov lint format typecheck pre-commit docker-build docker-up docker-down api example clean

install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all,dev]"

dev: install pre-commit
	pre-commit install

test:
	pytest

test-cov:
	pytest --cov=healthcare_agents --cov-report=term-missing --cov-report=html

lint:
	ruff check src tests examples scripts
	ruff format --check src tests examples scripts

format:
	ruff check --fix src tests examples scripts
	ruff format src tests examples scripts

pre-commit:
	pre-commit run --all-files

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

api:
	uvicorn healthcare_agents.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

chat:
	healthcare-chat -i

example:
	python examples/use_case_appointment_booking.py

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
