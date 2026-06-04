"""Storage package

The repository interface, the SQLite backend, and the
factory that hands routes a repository via FastAPI's Depends.
"""

from functools import lru_cache

from app.config import get_settings
from app.storage.base import MovieRepository
from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository
from app.storage.sqlite_repo import SqliteMovieRepository

__all__ = [
    "MovieRepository",
    "SqlAlchemyMovieRepository",
    "SqliteMovieRepository",
    "get_repository",
]


@lru_cache
def get_repository() -> MovieRepository:

    settings = get_settings()
    if settings.movies_backend == "sqlalchemy":
        repo = SqlAlchemyMovieRepository(settings.movies_db_path)
    else:
        repo = SqliteMovieRepository(settings.movies_db_path)
    repo.init_schema()
    return repo
