"""Storage package

The repository interface, the SQLite backend, and the
factory that hands routes a repository via FastAPI's Depends.
"""

from functools import lru_cache

from sqlalchemy import Engine

from app.config import get_settings
from app.storage.base import MovieRepository
from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository, make_engine
from app.storage.sqlite_repo import SqliteMovieRepository

__all__ = [
    "DEFAULT_USER_ID",
    "MovieRepository",
    "SqlAlchemyMovieRepository",
    "SqliteMovieRepository",
    "get_repository",
]


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().movies_db_path)


def dispose_engine() -> None:
    """Release the shared engine at shutdown. Only the ORM backend builds one."""
    if get_settings().movies_backend == "sqlalchemy":
        get_engine().dispose()
        get_engine.cache_clear()


DEFAULT_USER_ID = 1


@lru_cache
def get_repository() -> MovieRepository:

    settings = get_settings()
    if settings.movies_backend == "sqlalchemy":
        repo = SqlAlchemyMovieRepository(get_engine(), DEFAULT_USER_ID)
    else:
        repo = SqliteMovieRepository(settings.movies_db_path, DEFAULT_USER_ID)
    repo.init_schema()
    repo.ensure_user(DEFAULT_USER_ID, "default")
    return repo
