.PHONY: help install test lint format typecheck build clean run

# ── Default ──────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

# ── Help ─────────────────────────────────────────────────────────────
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup"
	@echo "  install      Install project and dev dependencies (uv sync)"
	@echo ""
	@echo "Development"
	@echo "  test         Run tests (uv run pytest)"
	@echo "  lint         Lint code (uv run ruff check)"
	@echo "  format       Format code (uv run ruff format)"
	@echo "  typecheck    Type check (uv run pyright)"
	@echo "  build        Build distribution packages (uv build)"
	@echo "  clean        Remove build artifacts and caches"
	@echo ""
	@echo "Usage"
	@echo "  run          Run a story through the pipeline (example)"

# ── Setup ────────────────────────────────────────────────────────────
install:
	uv sync

# ── Development ──────────────────────────────────────────────────────
test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run pyright src/

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# ── Usage ────────────────────────────────────────────────────────────
run:
	uv run rubric run "User Authentication" \
		--description "JWT-based authentication system" \
		--criteria "Users can register with email and password" \
		--criteria "Users can log in and receive a JWT token" \
		--criteria "Protected routes reject requests without a valid token"
