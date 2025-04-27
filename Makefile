.PHONY: setup run test lint clean docker-build docker-run docker-compose-up docker-compose-down migrate migrate-rollback

# Variables
PYTHON = python3
PIP = $(PYTHON) -m pip
APP_MODULE = app.main:app

# Setup local development
setup:
	$(PIP) install -r requirements.txt
	$(PYTHON) -c "import nltk; nltk.download('stopwords', quiet=True)"

# Run the application locally
run:
	uvicorn $(APP_MODULE) --reload

# Test
test:
	pytest

# Test with coverage
test-cov:
	pytest --cov=app --cov-report=term-missing

# Lint
lint:
	ruff check .

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
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(message)"

migrate-rollback:
	alembic downgrade -1

# Default target
all: lint test 