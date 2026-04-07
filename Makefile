# TransIQ Backend - Makefile
# Usage: make run | make test | make lint | make clean

.PHONY: run test lint clean install check health

# ── Server ──────────────────────────────────────
run:
	python main.py --reload

run-prod:
	python main.py --host 0.0.0.0 --port 8001 --no-reload

# ── Testing ─────────────────────────────────────
test:
	python -m pytest tests/ -v

test-quick:
	python -m pytest tests/ -x -q

test-cov:
	python -m pytest tests/ --cov=app --cov=core --cov=services --cov=pipelines --cov=agents --cov=domain -v

# ── Linting ─────────────────────────────────────
lint:
	python -m flake8 app/ core/ services/ pipelines/ agents/ domain/ --max-line-length=120

typecheck:
	python -m mypy app/ core/ services/ pipelines/ agents/ domain/

# ── Installation ────────────────────────────────
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"

# ── Health Checks ───────────────────────────────
health:
	python scripts/health_checks/check_db.py
	python scripts/health_checks/check_processing.py

check:
	python -c "from app.main import app; print('✅ App imports OK')"

# ── Cleanup ─────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage

# ── Docker ──────────────────────────────────────
docker-build:
	docker build -f infra/Dockerfile -t transiq-backend .

docker-up:
	docker-compose -f infra/docker-compose.yml up -d

docker-down:
	docker-compose -f infra/docker-compose.yml down
