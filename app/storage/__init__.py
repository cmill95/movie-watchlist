"""Storage package

The repository interface, the SQLite backend, and the
factory that hands routes a repository via FastAPI's Depends.
"""

from functools import lru_cache

from app.config import get_settings
from app.storage.base import MovieRepository
from app.storage.sqlite_repo import SqliteMovieRepository

__all__ = ["MovieRepository", "SqliteMovieRepository", "get_repository"]


@lru_cache
def get_repository() -> MovieRepository:

    repo = SqliteMovieRepository(get_settings().movies_db_path)
    repo.init_schema()
    return repo
