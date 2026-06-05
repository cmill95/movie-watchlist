"""Shared test bootstrap and fixtures."""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Set the SQLite test DB path before app modules are imported."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["MOVIES_DB_PATH"] = db_path


@pytest.fixture(scope="session", params=["sqlite", "sqlalchemy"])
def backend_repo(request):
    """One repository per backend, constructed once. Drives the MovieRepository
    contract test, which asserts both backends honor the same behavior.

    The SQLAlchemy backend gets its own DB file: its drop/recreate reset would
    otherwise clobber the schema the SQLite-backed API tests share.
    """
    from app.config import get_settings

    if request.param == "sqlite":
        from app.storage.sqlite_repo import SqliteMovieRepository

        repo = SqliteMovieRepository(get_settings().movies_db_path)
    else:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository

        repo = SqlAlchemyMovieRepository(path)

    repo.init_schema()
    yield repo
    repo.dispose()


@pytest.fixture
def repo(backend_repo):
    """A clean repository for each contract test, reset before use."""
    backend_repo.reset()
    return backend_repo


@pytest.fixture
def client():
    """TestClient for the API tests.

    Runs against a single backend (SQLite) to exercise the routes, validation,
    and wiring — backend conformance is the contract test's job, so the API
    tests don't fan out. The repo is injected via the dependency override and
    reset per test, keeping these hermetic (independent of MOVIES_BACKEND and
    the factory cache).
    """
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app
    from app.storage import get_repository
    from app.storage.sqlite_repo import SqliteMovieRepository

    repo = SqliteMovieRepository(get_settings().movies_db_path)
    repo.init_schema()
    repo.reset()
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
