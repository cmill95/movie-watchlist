![CI](https://github.com/cmill95/movie-watchlist/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![codecov](https://codecov.io/gh/cmill95/movie-watchlist/branch/main/graph/badge.svg)

# movie-watchlist

A small FastAPI + HTMX app for tracking movies you want to watch and movies you've watched. Each movie has a title, optional year, status (to-watch or watched), optional 1-10 rating, and optional notes. Data is persisted in a local SQLite database.

The app is multi-user: each user keeps their own watchlist. It ships with a single user named "Default"; from the UI you can switch users, add a new user (a name is required and must be unique), and rename the current user. The active user is tracked in a `user_id` cookie.


## Stack

- Python 3.12+ (CI runs against 3.12, 3.13, and 3.14)
- FastAPI for the backend
- HTMX for the interactive frontend (no JS framework, no build step)
- Jinja2 for server-rendered templates
- SQLite for storage, behind a `MovieRepository` interface with two interchangeable backends — stdlib `sqlite3` and SQLAlchemy 2.0
- Pydantic for request/response validation
- pytest for testing, with `pytest-cov` for coverage
- ruff for lint and format
- pre-commit for local commit-time checks
- just as the command runner for common dev tasks (run `just --list`)
- Docker for containerized builds (multi-stage, runs as a non-root user)
- GitHub Actions for CI (lint, format, and tests across a Python version matrix)
- Codecov for coverage reporting
- Dependabot for weekly dependency updates

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
- (Optional) [Docker](https://docs.docker.com/get-docker/), if you'd rather run the app in a container than locally.
- (Optional) [`just`](https://github.com/casey/just) as a command runner for the project's dev tasks. Install with `uv tool install rust-just`, then run `just --list` to see the available recipes.

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

### Run against Postgres

The default backend is SQLite — a local file, no setup. To run against Postgres instead, start the bundled database, apply migrations, then point the app at it:

```sh
# start a local Postgres (docker compose; data persists in a named volume)
just db-up

# select the Postgres backend (copy the template, then edit the values below)
cp .env.example .env
#   MOVIES_BACKEND=postgres
#   DATABASE_URL=postgresql+psycopg://movies:movies@localhost:5433/movies

# apply migrations, then run the app
just migrate
just run
```

Unlike SQLite, the Postgres schema is **not** created on startup — Alembic owns it, applied by `just migrate` (`alembic upgrade head`). Booting against an unmigrated database fails loudly. After changing the ORM models, generate a migration with `just new-migration name="add something"` and review it before committing. Stop the database with `just db-down` (keeps data) or `just db-nuke` (deletes the volume).

### Run with Docker

The app ships with a multi-stage `Dockerfile` (built on `python:3.14-slim`) that runs as a non-root user and includes a `HEALTHCHECK` against the `/health` endpoint.

```sh
# build the image
docker build -t movie-watchlist .

# run it in the background, mapping host port 8000 -> container port 8000
docker run -d -p 8000:8000 --name mw movie-watchlist
```

Then visit <http://localhost:8000> and the liveness check at <http://localhost:8000/health>.

```sh
# inspect or tear down the container
docker logs mw        # view output (add -f to follow)
docker stop mw        # stop it
docker rm mw          # remove it (add -f to force-remove a running one)
```

### Container image

Every pull request builds the multi-stage image to catch Dockerfile
regressions before merge. Pushes to `main` additionally publish it to the
GitHub Container Registry (GHCR), tagged `latest` and with the commit SHA, then
scan it for critical/high CVEs with Trivy.

Pull and run the published image instead of building locally:

```sh
docker pull ghcr.io/cmill95/movie-watchlist:latest
docker run -d -p 8000:8000 --name mw ghcr.io/cmill95/movie-watchlist:latest
```

Published images are listed under the repo's
[Packages](https://github.com/cmill95/movie-watchlist/pkgs/container/movie-watchlist).

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

| Method | Path                          | Returns                          |
|--------|-------------------------------|----------------------------------|
| GET    | `/`                           | Full page                        |
| POST   | `/ui/movies`                  | New movie row                    |
| GET    | `/ui/movies/{movie_id}`       | Movie row (read mode)            |
| GET    | `/ui/movies/{movie_id}/edit`  | Movie row (edit mode)            |
| PATCH  | `/ui/movies/{movie_id}`       | Movie row (read mode)            |
| DELETE | `/ui/movies/{movie_id}`       | Empty 200 response               |
| POST   | `/ui/switch-user`             | Sets `user_id` cookie, redirects |
| POST   | `/ui/users`                   | Adds a user, switches to them    |
| GET    | `/ui/users/{user_id}`         | Current-user name (read mode)    |
| GET    | `/ui/users/{user_id}/edit`    | Current-user name (edit mode)    |
| PATCH  | `/ui/users/{user_id}`         | Renames the user, redirects      |

Adding or renaming a user requires a non-empty name and rejects duplicates with `409 Conflict`.

## Storage

The data layer sits behind a `MovieRepository` protocol (`app/storage/base.py`) declaring the five operations the routes use — `create`, `get`, `list_all`, `update`, `delete`. Two interchangeable backends implement it:

- `SqliteMovieRepository` — stdlib `sqlite3`, with a hand-written schema and SQL.
- `SqlAlchemyMovieRepository` — the same operations on the SQLAlchemy 2.0 ORM.

Both persist to a SQLite file. `MOVIES_BACKEND` (`sqlite` or `sqlalchemy`, default `sqlite`) selects one at runtime, injected through `Depends(get_repository)`, so the routes never know which is in use. Lifecycle methods (`init_schema`, `reset`, `dispose`) live on the concrete classes, not the protocol — they're setup/teardown concerns, not route operations.

User management lives on the concrete repositories too, deliberately off the `MovieRepository` protocol: `ensure_user`, `create_user`, `get_user`, `rename_user`, and `list_users`. Movies are scoped to their owner via a `user_id` foreign key, and each repository is bound to one user at construction. `create_user`/`rename_user` raise `DuplicateUserName` on a name collision (the routes translate it to `409`). On startup, `init_storage` seeds a single user named "Default".

### Notes on building both backends

Writing the app against both backends surfaced where the abstraction holds and where it leaks.


The main issue encountered was with `test_storage.py` which hit the raw `sqlite3` backend directly, this did not map cleanly with SQLAlchemy, as this backend made no integrity constraint guarentees. For this reason, `test_storage.py` was removed and `test_repository.py` was added, hitting both backends cleanly. Also, the integrity constraints guarenteed by the raw `sqlite3` backend were removed, now both solely rely on the Pydantic models to validate incoming data.

Where I'd land if forced to pick: for an app this small, raw `sqlite3` — no dependency, nothing hidden. For the larger system with a growing schema, relationships, and migrations via Alembic, the ORM's lower boilerplate and tooling would win.

## Development

Common dev tasks are wrapped as [`just`](https://github.com/casey/just) recipes — run `just --list` to see them all (`just install`, `just test`, `just lint`, `just format`, and so on). The recipes are thin wrappers over the `uv run ...` commands below, so you can run those directly if you'd rather not install `just`:

```sh
# install the pre-commit hook (runs ruff on every commit)
uv run pre-commit install

# run tests
uv run pytest

# lint and format
uv run ruff check .
uv run ruff format .
```

The in-process tests are split into API tests (`test_movies.py`, exercising the routes via `TestClient` against the default backend) and `MovieRepository` contract tests (`test_repository.py`, asserting behavioral conformance against both backends via a parametrized fixture). Coverage settings live in `pyproject.toml` — branch coverage, `term-missing` output, and a `--cov-fail-under` floor so coverage can't silently regress.

End-to-end tests (`tests/e2e/test_container.py`) are out-of-process: they start the built Docker image and drive it over real HTTP with `httpx`, proving the deployed artifact works rather than just the code that goes into it. Because they exercise the container instead of the local app, they're excluded from coverage and deselected from the default `pytest` run via an `e2e` marker. Run them against a container listening on `http://localhost:8000` (override the target with `E2E_BASE_URL`):

```sh
uv run pytest tests/e2e -m e2e --no-cov
```

## Continuous integration

On every pull request, GitHub Actions runs ruff (lint + format check) and pytest across Python 3.12 / 3.13 / 3.14, plus the pre-commit hooks. A `ci-passed` aggregator job gives branch protection a single stable check to require. Coverage reports are uploaded to Codecov.

The pipeline then builds the Docker image — on every PR, so a broken Dockerfile fails the PR — and runs the end-to-end suite against it. The built image is handed to a separate `e2e` job as an artifact, which loads it, starts the container, waits on `/health`, and runs `tests/e2e`. Publishing to GHCR happens only on pushes to `main`.
