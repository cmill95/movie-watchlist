# Show available recipes (the default when running `just`)
default:
    @just --list

# Install dependencies and pre-commit hooks
install:
    uv sync --all-extras --dev
    uv run pre-commit install

# Start dev server with reload
run:
    uv run fastapi dev app/main.py

# Run tests
test:
    uv run pytest

# Run tests with HTML coverage report
test-cov:
    uv run pytest --cov-report=html
    @echo "Coverage report: htmlcov/index.html"

# Run ruff lint
lint:
    uv run ruff check .

# Format code with ruff
format:
    uv run ruff format .

# Run ty type checker
typecheck:
    uv run ty check

# Run all pre-commit hooks
pre-commit:
    uv run pre-commit run --all-files

# Build docker image
build:
    docker build -t movie-watchlist .

# Run docker container locally
docker-run:
    docker run -p 8000:8000 movie-watchlist

# Remove caches and build artifacts
clean:
    rm -rf .pytest_cache .ruff_cache htmlcov .coverage coverage.xml
    find . -type d -name __pycache__ -exec rm -rf {} +
