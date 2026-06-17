"""SQLite (stdlib sqlite3) implementation of the movie repository.

The original storage.py logic, now a class satisfying the MovieRepository
protocol (app/storage/base.py). Behavior is unchanged.

init_schema() and reset() are instance methods but deliberately NOT on the
protocol — lifecycle/test concerns, not route operations.

Validation is duplicated with the Pydantic models (app/models.py) and the
CHECK constraints below; change one, must change the other.
"""

import contextlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.models import MovieCreate, MovieRead, MovieUpdate, User

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS movies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    title       TEXT    NOT NULL,
    year        INTEGER,
    status      TEXT    NOT NULL,
    rating      INTEGER,
    notes       TEXT,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""

# Columns that are safe to include in a dynamic UPDATE.
# This is a whitelist — column names are interpolated into the SQL string,
# so they must NEVER come from untrusted input. Keep this in sync with the
# MovieUpdate model.
_UPDATABLE_COLUMNS = {"title", "year", "status", "rating", "notes"}


def _open(db_path: Path | str) -> sqlite3.Connection:
    """Open a new connection with our standard config (Row factory, FKs on)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> datetime:
    return datetime.now(UTC)


def _row_to_movie(row: sqlite3.Row) -> MovieRead:
    """sqlite3.Row -> MovieRead, parsing ISO-8601 text back into datetimes."""

    data = dict(row)
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
    return MovieRead.model_validate(data)


class SqliteMovieRepository:
    """MoiveRepository backed by stdlib sqlite3 (no ORM)."""

    def __init__(self, db_path: Path | str, user_id: int) -> None:
        self._db_path = Path(db_path)
        self._user_id = user_id

    # Added for convience, thin wrapper for _open()
    def _connect(self) -> sqlite3.Connection:
        return _open(self._db_path)

    # --- Lifecycle ---

    def init_schema(self) -> None:
        """Create the movies table if absent."""
        with contextlib.closing(self._connect()) as conn, conn:
            conn.executescript(_SCHEMA)

    def reset(self) -> None:
        """Clear all movies and reset the id sequence. For tests."""
        with contextlib.closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM movies")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'movies'")

    def ensure_user(self, user_id: int, name: str) -> None:
        with contextlib.closing(self._connect()) as conn, conn:
            conn.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, name))

    def list_users(self) -> list[User]:
        with contextlib.closing(self._connect()) as conn:
            rows = conn.execute("SELECT id, name FROM users ORDER BY id ASC").fetchall()
        return [User(id=row["id"], name=row["name"]) for row in rows]

    # --- MovieRepository protocol

    def create(self, data: MovieCreate) -> MovieRead:
        now = _now().isoformat()
        with contextlib.closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                """
                INSERT INTO movies (
                    user_id, title, year, status,
                    rating, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._user_id,
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

    def get(self, movie_id: int) -> MovieRead | None:
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM movies WHERE id = ? AND user_id = ?", (movie_id, self._user_id)
            ).fetchone()
        return _row_to_movie(row) if row is not None else None

    def list_all(self) -> list[MovieRead]:
        with contextlib.closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM movies WHERE user_id = ? ORDER BY id ASC",
                (self._user_id,),
            ).fetchall()
        return [_row_to_movie(row) for row in rows]

    def update(self, movie_id: int, data: MovieUpdate) -> MovieRead | None:
        changes = data.model_dump(exclude_unset=True)

        if "status" in changes:
            changes["status"] = changes["status"].value
        changes["updated_at"] = _now().isoformat()

        columns = [c for c in changes if c in _UPDATABLE_COLUMNS or c == "updated_at"]
        set_clause = ", ".join(f"{c} = ?" for c in columns)
        values = [changes[c] for c in columns]

        with contextlib.closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                f"UPDATE movies SET {set_clause} WHERE id = ? AND user_id = ?",
                (*values, movie_id, self._user_id),
            )
            if cursor.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM movies WHERE id = ? AND user_id = ?", (movie_id, self._user_id)
            ).fetchone()
        return _row_to_movie(row)

    def delete(self, movie_id: int) -> bool:
        with contextlib.closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "DELETE FROM movies WHERE id = ? AND user_id = ?", (movie_id, self._user_id)
            )
        return cursor.rowcount > 0
