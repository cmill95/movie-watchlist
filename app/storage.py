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

from datetime import UTC, datetime

from app.models import MovieCreate, MovieRead, MovieUpdate

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
