.PHONY: help install install-dev lint format test coverage clean docs

help:
	@echo "Health Insurance Analytics Platform - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make lint             - Run code linters (flake8, pylint, mypy)"
	@echo "  make format           - Format code (black, isort)"
	@echo "  make test             - Run tests with pytest"
	@echo "  make coverage         - Generate coverage report"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove generated files and caches"
	@echo "  make clean-all        - Remove venv and all generated files"

# Installation targets
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

pre-commit-install:
	pre-commit install

# Linting & Formatting
lint:
	@echo "Running flake8..."
	flake8 src/ tests/
	@echo "Running pylint..."
	pylint src/
	@echo "Running mypy..."
	mypy src/

format:
	@echo "Formatting with black..."
	black src/ tests/
	@echo "Sorting imports with isort..."
	isort src/ tests/

# Testing
test:
	pytest tests/ -v

coverage:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name .coverage -delete
	rm -rf dist/ build/ *.egg-info/

clean-all: clean
	rm -rf venv/ .venv/

# Documentation
docs:
	@echo "Documentation is in Project_Documentation/ folder"
	@echo "Start with: Project_Documentation/PROJECT_OVERVIEW.md"
