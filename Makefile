# Makefile for Spark project

.PHONY: test lint build clean install dev release

# Default target
all: test

# Run tests with coverage
test:
	PYTHONPATH=src pytest tests/ --cov=spark --cov-report=term-missing

# Run linting
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

# Format code
format:
	ruff format src/ tests/

# Install development dependencies
dev:
	uv sync --extra dev

# Install production dependencies
install:
	uv sync

# Build Python package
build:
	uv build

# Clean build artifacts
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run CI locally (simulate GitHub Actions)
ci-local: lint test build

# Create release tag
release:
	@echo "Current version:"
	@grep "version =" pyproject.toml
	@read -p "Enter new version (e.g., 0.2.0): " v; \
	git tag -a v$$v -m "Release v$$v"; \
	git push origin v$$v

# Show help
help:
	@echo "Available targets:"
	@echo "  test       - Run tests with coverage"
	@echo "  lint       - Run linting checks"
	@echo "  format     - Format code with ruff"
	@echo "  dev        - Install dev dependencies"
	@echo "  install    - Install production dependencies"
	@echo "  build      - Build Python package"
	@echo "  clean      - Clean build artifacts"
	@echo "  ci-local   - Run CI checks locally"
	@echo "  release    - Create and push release tag"