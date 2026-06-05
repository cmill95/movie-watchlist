"""Tests for the repository factory (app/storage/__init__.py).

get_repository selects the backend from MOVIES_BACKEND. The contract tests
construct backends directly and the API tests override the dependency, so the
selection logic is only exercised here.
"""

import pytest

from app.config import get_settings
from app.storage import SqlAlchemyMovieRepository, SqliteMovieRepository, get_repository


@pytest.mark.parametrize(
    ("backend", "expected"),
    [
        ("sqlite", SqliteMovieRepository),
        ("sqlalchemy", SqlAlchemyMovieRepository),
    ],
)
def test_get_repository_selects_backend(backend, expected, monkeypatch):
    monkeypatch.setenv("MOVIES_BACKEND", backend)
    # get_settings and get_repository are both lru_cached; clear so the new
    # MOVIES_BACKEND is read, and clear again after so the cache isn't polluted
    # for other tests.
    get_settings.cache_clear()
    get_repository.cache_clear()

    repo = get_repository()
    try:
        assert isinstance(repo, expected)
    finally:
        repo.dispose()
        get_settings.cache_clear()
        get_repository.cache_clear()
