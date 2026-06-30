"""Tests for the repository factory (app/storage/__init__.py).

make_repository selects the backend from MOVIES_BACKEND. The contract tests
construct backends directly and the API tests override the dependency, so the
selection logic is only exercised here.
"""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app import storage
from app.config import Settings, get_settings
from app.storage import (
    DEFAULT_USER_ID,
    DEFAULT_USER_NAME,
    SqlAlchemyMovieRepository,
    SqliteMovieRepository,
    dispose_engine,
    init_storage,
    make_repository,
)


@pytest.mark.parametrize(
    ("backend", "expected"),
    [
        ("sqlite", SqliteMovieRepository),
        ("postgres", SqlAlchemyMovieRepository),
    ],
)
def test_make_repository_selects_backend(backend, expected, monkeypatch):
    monkeypatch.setenv("MOVIES_BACKEND", backend)
    # A dummy DSN for the postgres branch: create_engine is lazy and never
    # connects here, so no live Postgres is needed to assert backend selection.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/movies")
    # get_settings is lru_cached; clear so the new MOVIES_BACKEND is read.
    # make_repository isn't cached, so there's nothing to clear for it.
    get_settings.cache_clear()

    repo = make_repository(DEFAULT_USER_ID)
    try:
        assert isinstance(repo, expected)
    finally:
        dispose_engine()
        get_settings.cache_clear()


def test_postgres_backend_requires_database_url(monkeypatch):
    """Selecting postgres without a DSN fails loudly at config-load time."""
    monkeypatch.setenv("MOVIES_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Disable .env loading for this construction: a developer's .env could
    # otherwise supply DATABASE_URL and mask the validation error this asserts.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        Settings()


def test_init_storage_skips_schema_creation_for_postgres(monkeypatch):
    """Postgres schema is owned by Alembic, so boot must not call init_schema.
    Seeding the default user still runs (it's idempotent)."""
    monkeypatch.setenv("MOVIES_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/movies")
    get_settings.cache_clear()

    repo = MagicMock()
    monkeypatch.setattr(storage, "make_repository", lambda user_id: repo)

    try:
        init_storage()
    finally:
        get_settings.cache_clear()

    repo.init_schema.assert_not_called()
    repo.ensure_user.assert_called_once_with(DEFAULT_USER_ID, DEFAULT_USER_NAME)
