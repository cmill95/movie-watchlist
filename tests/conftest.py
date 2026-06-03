"""Shared test bootstrap and fixtures"""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Set test DB path before app modules are imported."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["MOVIES_DB_PATH"] = db_path


@pytest.fixture(scope="session")
def repo():
    """The concrete SQLite repository pointed at the test DB.

    Constructed directly, not via get_repository, because tests need reset()
    """

    from app.config import get_settings
    from app.storage.sqlite_repo import SqliteMovieRepository

    return SqliteMovieRepository(get_settings().movies_db_path)


@pytest.fixture(scope="session", autouse=True)
def _init_schema(repo):
    """Create the schema once per test session."""
    repo.init_schema()


@pytest.fixture(autouse=True)
def _reset(repo):
    """Clear movies between tests."""
    repo.reset()


@pytest.fixture(scope="session")
def client():
    """A FastAPI TestClient."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
