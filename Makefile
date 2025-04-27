.PHONY: setup run test lint clean docker-build docker-run docker-compose-up docker-compose-down migrate migrate-rollback pre-commit pre-commit-install pre-commit-run poetry-install poetry-update requirements

# Variables
PYTHON = python3
PIP = $(PYTHON) -m pip
APP_MODULE = app.main:app

# Setup local development with Poetry
setup:
	poetry install
	$(PYTHON) -c "import nltk; nltk.download('stopwords', quiet=True)"
	pre-commit install

# Старая настройка с pip
setup-pip:
	$(PIP) install -r requirements.txt
	$(PYTHON) -c "import nltk; nltk.download('stopwords', quiet=True)"
	pre-commit install

# Poetry commands
poetry-install:
	poetry install

poetry-update:
	poetry update

# Generate requirements.txt from pyproject.toml
requirements:
	poetry export -f requirements.txt --output requirements.txt --without-hashes
	@echo "Requirements files updated successfully"

# Автоматически обновлять requirements.txt при изменении pyproject.toml
requirements.txt: pyproject.toml
	$(MAKE) requirements

# Run the application locally
run:
	poetry run uvicorn $(APP_MODULE) --reload

# Test
test:
	poetry run pytest

# Test with coverage
test-cov:
	poetry run pytest --cov=app --cov-report=term-missing

# Lint
lint:
	poetry run ruff check .

# Clean
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf app/__pycache__
	rm -rf app/services/__pycache__
	rm -rf .coverage

# Docker standalone
docker-build:
	docker build -t tfidf-app .

docker-run:
	docker run -p 8000:8000 tfidf-app

# Docker Compose - для разработки и запуска всего окружения
docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

docker-compose-build:
	docker-compose build

docker-compose-logs:
	docker-compose logs -f

# Database migrations
migrate:
	poetry run alembic upgrade head

migrate-create:
	poetry run alembic revision --autogenerate -m "$(message)"

migrate-rollback:
	poetry run alembic downgrade -1

# Default target
all: lint test

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files
