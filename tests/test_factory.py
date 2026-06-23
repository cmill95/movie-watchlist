"""Tests for the repository factory (app/storage/__init__.py).

make_repository selects the backend from MOVIES_BACKEND. The contract tests
construct backends directly and the API tests override the dependency, so the
selection logic is only exercised here.
"""

import pytest

from app.config import get_settings
from app.storage import (
    DEFAULT_USER_ID,
    SqlAlchemyMovieRepository,
    SqliteMovieRepository,
    dispose_engine,
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
