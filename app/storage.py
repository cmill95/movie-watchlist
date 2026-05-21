"""
In-memory storage for movies.

This is a throwaway implementation — a module-level dict keyed by id, with
a simple integer counter for id generation. It will be replaced with a real
database (SQLite, then Postgres) later. The interface here is intentionally
narrow so the swap is straightforward: routes call create/get/list/update/
delete, and the implementation details stay hidden.

Known limitations:
- State lives in module-level globals, so it does not survive process restart.
- State is shared across tests unless explicitly cleared (handled by a pytest
  fixture in tests/test_movies.py).
- Not thread-safe. FastAPI's default sync routes don't share state across
  threads in a way that would expose this, but it's worth knowing.
"""

import contextlib
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.models import MovieCreate, MovieRead, MovieUpdate

# --- SQLite scaffolding (not yet used by the public functions) ---

_DEFAULT_DB_PATH = "movies.db"


def _db_path() -> Path:
    """Resolve the DB path at call time, not import time.

    Reading the env var on each call lets tests override MOVIES_DB_PATH
    before any storage function runs, without needing to mutate
    module-level state from the test fixture.
    """
    return Path(os.environ.get("MOVIES_DB_PATH", _DEFAULT_DB_PATH))


def _connect() -> sqlite3.Connection:
    """Open a new SQLite connection with our standard configuration.

    - row_factory = sqlite3.Row lets us access columns by name (row["title"])
      instead of by tuple index (row[1]). Much easier to read and refactor.
    - PRAGMA foreign_keys = ON enables foreign key constraint enforcement.
      SQLite ships with this OFF by default for backwards compatibility, so
      we have to opt in on every connection. We don't have any FKs yet, but
      turning it on now means we won't forget when we add a second table.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Validation rules are duplicated with Pydantic models in app/models.py
# (Title, Year, Rating, Notes, MovieStatus). When changing rules in one
# place, update the other.

_SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    year        INTEGER          CHECK (year IS NULL OR year BETWEEN 1888 AND 2100),
    status      TEXT    NOT NULL CHECK (status IN ('to_watch', 'watched')),
    rating      INTEGER          CHECK (rating IS NULL OR rating BETWEEN 1 AND 10),
    notes       TEXT             CHECK (notes IS NULL OR length(notes) BETWEEN 1 AND 2000),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
)
"""


def init_db() -> None:
    """Create the movies table if it doesn't exist.

    Idempotent — safe to call on every app startup and from test fixtures.
    Called from the FastAPI lifespan handler in main.py (added later) and
    from the test fixture (added later).
    """
    with contextlib.closing(_connect()) as conn:
        with conn:
            conn.execute(_SCHEMA)


def _row_to_movie(row: sqlite3.Row) -> MovieRead:
    """Convert a sqlite3.Row into a MovieRead.

    Two conversions happen here:
    1. sqlite3.Row -> dict, because Pydantic's from_attributes=True uses
       getattr() to read fields, and sqlite3.Row supports row["col"] but
       NOT row.col. dict(row) gives us a mapping that model_validate
       accepts directly.
    2. ISO-8601 strings -> datetime objects, because we store datetimes
       as TEXT in SQLite (no native datetime type). Pydantic will accept
       a datetime here; it would also accept the string and parse it,
       but doing it explicitly makes the conversion visible.
    """

    data = dict(row)
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
    return MovieRead.model_validate(data)


# Module-level state. Reset via reset_storage() in tests.
_movies: dict[int, MovieRead] = {}
_next_id: int = 1


def reset_storage() -> None:
    """Clear all movies and reset the id counter. For tests."""
    global _next_id
    _movies.clear()
    _next_id = 1


def _now() -> datetime:
    return datetime.now(UTC)


def create(data: MovieCreate) -> MovieRead:
    """Create a new movie. Server sets id, created_at, updated_at."""
    global _next_id
    now = _now()
    movie = MovieRead(
        id=_next_id,
        title=data.title,
        year=data.year,
        status=data.status,
        rating=data.rating,
        notes=data.notes,
        created_at=now,
        updated_at=now,
    )

    _movies[_next_id] = movie
    _next_id += 1
    return movie


def get(movie_id: int) -> MovieRead | None:
    """Return the movie with this id, or None if not found."""
    return _movies.get(movie_id)


def list_all() -> list[MovieRead]:
    """Return all movies, ordered by id ascending"""
    return [_movies[i] for i in sorted(_movies)]


def update(movie_id: int, data: MovieUpdate) -> MovieRead | None:
    """Apply a partial update. Returns the updated movie, or None if not found."""
    existing = _movies.get(movie_id)
    if existing is None:
        return None

    changes = data.model_dump(exclude_unset=True)
    updated = existing.model_copy(update={**changes, "updated_at": _now()})
    _movies[movie_id] = updated
    return updated


def delete(movie_id: int) -> bool:
    """Delete the movie. Returns True if deleted, False if not found."""
    if movie_id not in _movies:
        return False
    del _movies[movie_id]
    return True
