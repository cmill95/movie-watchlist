"""
SQLite storage for movies.

Persists movies to a SQLite database file (path from MOVIES_DB_PATH env var,
defaulting to ./movies.db). The interface is intentionally narrow — routes
call create/get/list/update/delete, and the SQL details stay hidden behind
this module. No ORM; stdlib sqlite3 only.

Conventions used here:
- A new connection is opened per call (no module-level connection). Simple
  and thread-safe at the cost of a tiny connection-open overhead.
- Writes are wrapped in `with conn:` for automatic commit/rollback.
- Connections are wrapped in `contextlib.closing(...)` so they close on exit.
- Datetimes are stored as ISO-8601 strings (SQLite has no datetime type).
- The MovieStatus enum is stored as its string value.
- Schema is created idempotently via init_db(), called from main.py's
  lifespan handler at app startup and from the test fixture.

Defense in depth: validation lives both in the Pydantic models (app/models.py)
and as CHECK constraints in the schema below. When changing one, update the
other.

Known limitations:
- No connection pooling. Fine for SQLite; will need rethinking with Postgres.
- No migrations — schema changes require deleting the DB file. Fine for now;
  a real migration tool (Alembic, etc.) is a future concern.
"""

import contextlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models import MovieCreate, MovieRead, MovieUpdate


def _db_path() -> Path:
    """DB path is provided by Settings class in app/config.py"""
    return Path(get_settings().movies_db_path)


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
    Called from the FastAPI lifespan handler in main.py and
    from the test fixture (must add later).
    """
    with contextlib.closing(_connect()) as conn, conn:
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


def reset_storage() -> None:
    """Clear all movies and reset the id sequence. For tests."""
    with contextlib.closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM movies")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'movies'")


def _now() -> datetime:
    return datetime.now(UTC)


def create(data: MovieCreate) -> MovieRead:
    """Create a new movie. Server sets id, created_at, updated_at."""
    now = _now().isoformat()
    with contextlib.closing(_connect()) as conn, conn:
        cursor = conn.execute(
            """
                INSERT INTO movies (title, year, status, rating, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
            (
                data.title,
                data.year,
                data.status.value,
                data.rating,
                data.notes,
                now,
                now,
            ),
        )
        new_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM movies WHERE id = ?", (new_id,)).fetchone()
    return _row_to_movie(row)


def get(movie_id: int) -> MovieRead | None:
    """Return the movie with this id, or None if not found."""
    with contextlib.closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if row is None:
        return None
    return _row_to_movie(row)


def list_all() -> list[MovieRead]:
    """Return all movies, ordered by id ascending."""
    with contextlib.closing(_connect()) as conn:
        rows = conn.execute("SELECT * FROM movies ORDER BY id ASC").fetchall()
    return [_row_to_movie(row) for row in rows]


# Columns that are safe to include in a dynamic UPDATE.
# This is a whitelist — column names are interpolated into the SQL string,
# so they must NEVER come from untrusted input. Keep this in sync with the
# MovieUpdate model.
_UPDATABLE_COLUMNS = {"title", "year", "status", "rating", "notes"}


def update(movie_id: int, data: MovieUpdate) -> MovieRead | None:
    """Apply a partial update. Returns the updated movie, or None if not found."""
    changes = data.model_dump(exclude_unset=True)

    # Serialize the enum to its string value. Other types (int, str, None)
    # pass through to sqlite3 as-is.
    if "status" in changes:
        changes["status"] = changes["status"].value

    # Always bump updated_at, even on an empty-body PATCH (matches existing behavior).
    changes["updated_at"] = _now().isoformat()

    # Build "col1 = ?, col2 = ?, ..." from the changed columns.
    # Filter against the whitelist defensively — model_dump should only emit
    # known fields, but treating the SQL string as untrusted is the defensive approach
    columns = [c for c in changes if c in _UPDATABLE_COLUMNS or c == "updated_at"]
    set_clause = ", ".join(f"{c} = ?" for c in columns)
    values = [changes[c] for c in columns]

    with contextlib.closing(_connect()) as conn, conn:
        cursor = conn.execute(
            f"UPDATE movies SET {set_clause} WHERE id = ?",
            (*values, movie_id),
        )
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    return _row_to_movie(row)


def delete(movie_id: int) -> bool:
    """Delete the movie. Returns True if deleted, False if not found."""
    with contextlib.closing(_connect()) as conn, conn:
        cursor = conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    return cursor.rowcount > 0
