"""Shared test bootstrap and fixtures"""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Set test DB path before app modules are imported."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["MOVIES_DB_PATH"] = db_path


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Create the schema once per test session."""
    from app.storage import init_db

    init_db()


@pytest.fixture(autouse=True)
def _reset_storage():
    """Clear movies between tests."""
    from app.storage import reset_storage

    reset_storage()


@pytest.fixture(scope="session")
def client():
    """A FastAPI TestClient."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
