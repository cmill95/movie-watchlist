# movie-watchlist

A throwaway FastAPI app built during Week 1 of my summer internship. The point isn't the movie tracker itself — it's the stack and the development workflow (uv, ruff, pre-commit, pytest, GitHub Actions CI) that the real project will use later.

## Stack

- Python 3.12
- FastAPI for the backend
- Jinja2 for server-rendered templates
- pytest for testing
- ruff for lint and format
- pre-commit for local commit-time checks
- GitHub Actions for CI

## Development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
# install dependencies
uv sync --all-extras --dev

# install pre-commit hook
uv run pre-commit install

# run tests
uv run pytest

# lint and format
uv run ruff check .
uv run ruff format .
```