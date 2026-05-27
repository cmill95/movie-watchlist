![CI](https://github.com/cmill95/movie-watchlist/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![codecov](https://codecov.io/gh/cmill95/movie-watchlist/branch/main/graph/badge.svg)

# movie-watchlist

A small FastAPI + HTMX app for tracking movies you want to watch and movies you've watched. Each movie has a title, optional year, status (to-watch or watched), optional 1-10 rating, and optional notes. Data is persisted in a local SQLite database.

> Context: this is a throwaway project built during Week 1 of my summer internship.

## Stack

- Python 3.12
- FastAPI for the backend
- HTMX for the interactive frontend (no JS framework, no build step)
- Jinja2 for server-rendered templates
- SQLite for storage (via the standard-library `sqlite3` module)
- Pydantic for request/response validation
- pytest for testing
- ruff for lint and format
- pre-commit for local commit-time checks
- GitHub Actions for CI

## Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) for dependency management. Install with:

  ```sh
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

  See the [uv install docs](https://docs.astral.sh/uv/getting-started/installation/) for other options (Homebrew, pipx, etc.).

## Getting started

```sh
# clone the repo
git clone https://github.com/cmill95/movie-watchlist.git
cd movie-watchlist

# install dependencies (uses uv.lock for reproducible versions)
uv sync --all-extras --dev

# run the app
uv run fastapi dev app/main.py
```

The app will be available at <http://127.0.0.1:8000>. FastAPI's auto-generated API docs are at <http://127.0.0.1:8000/docs>.

## API

The app exposes two parallel sets of endpoints: a JSON API for programmatic access, and an HTMX/HTML API used by the browser UI.

### JSON endpoints

| Method | Path                  | Description                |
|--------|-----------------------|----------------------------|
| GET    | `/health`             | Liveness check             |
| GET    | `/movies`             | List all movies            |
| POST   | `/movies`             | Create a movie             |
| GET    | `/movies/{movie_id}`  | Get a single movie         |
| PATCH  | `/movies/{movie_id}`  | Partially update a movie   |
| DELETE | `/movies/{movie_id}`  | Delete a movie             |

### HTMX endpoints

These return HTML fragments and are consumed by the browser UI, not intended for direct use.

| Method | Path                          | Returns                  |
|--------|-------------------------------|--------------------------|
| GET    | `/`                           | Full page                |
| POST   | `/ui/movies`                  | New movie row            |
| GET    | `/ui/movies/{movie_id}`       | Movie row (read mode)    |
| GET    | `/ui/movies/{movie_id}/edit`  | Movie row (edit mode)    |
| PATCH  | `/ui/movies/{movie_id}`       | Movie row (read mode)    |
| DELETE | `/ui/movies/{movie_id}`       | Empty 200 response       |

## Development

```sh
# install the pre-commit hook (runs ruff on every commit)
uv run pre-commit install

# run tests
uv run pytest

# lint and format
uv run ruff check .
uv run ruff format .
```
