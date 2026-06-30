"""Storage package

The repository interface, the SQLite backend, and the
factory that hands routes a repository via FastAPI's Depends.
"""

from functools import lru_cache

from sqlalchemy import Engine

from app.config import get_settings
from app.storage.base import DuplicateUserName, MovieRepository
from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository, make_engine
from app.storage.sqlite_repo import SqliteMovieRepository

__all__ = [
    "DEFAULT_USER_ID",
    "DuplicateUserName",
    "MovieRepository",
    "SqlAlchemyMovieRepository",
    "SqliteMovieRepository",
    "init_storage",
    "make_repository",
]


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


def dispose_engine() -> None:
    """Release the shared engine at shutdown. Only the ORM backend builds one."""
    if get_settings().movies_backend == "postgres":
        get_engine().dispose()
        get_engine.cache_clear()


DEFAULT_USER_ID = 1


def make_repository(user_id: int) -> SqliteMovieRepository | SqlAlchemyMovieRepository:
    """Build a repository bound to a user. Returns the concrete backend so the
    off-Protocol lifecycle methods (init_schema/ensure_user) stay reachable for
    init_storage; the route-facing Protocol boundary is get_repository in main."""
    settings = get_settings()
    if settings.movies_backend == "postgres":
        return SqlAlchemyMovieRepository(get_engine(), user_id)
    return SqliteMovieRepository(settings.movies_db_path, user_id)


DEFAULT_USER_NAME = "Default"


def init_storage() -> None:
    """One-time startup. Seeds the default user; for SQLite it also creates the schema.

    The Postgres schema is managed by Alembic (`alembic upgrade head`, run as a
    deploy step before the app starts), so we deliberately do not create_all here.
    Seeding stays on boot for both backends: it's idempotent (ensure_user checks
    first), and against an unmigrated Postgres it fails loudly, signaling that
    migrations have not been run.

    The app ships with a single user named "Default"; clients add more from the UI."""
    settings = get_settings()
    repo = make_repository(DEFAULT_USER_ID)
    if settings.movies_backend == "sqlite":
        repo.init_schema()
    repo.ensure_user(DEFAULT_USER_ID, DEFAULT_USER_NAME)
