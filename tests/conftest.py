"""Shared test bootstrap and fixtures."""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Set the SQLite test DB path before app modules are imported."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["MOVIES_DB_PATH"] = db_path


_TEST_USER_ID = 1


@pytest.fixture(scope="session", params=["sqlite", "sqlalchemy"])
def backend_repo(request):
    """One repository per backend, constructed once. Drives the MovieRepository
    contract test, which asserts both backends honor the same behavior.

    The SQLAlchemy backend gets its own DB file: its drop/recreate reset would
    otherwise clobber the schema the SQLite-backed API tests share.
    """
    from app.config import get_settings

    engine = None
    if request.param == "sqlite":
        from app.storage.sqlite_repo import SqliteMovieRepository

        repo = SqliteMovieRepository(get_settings().movies_db_path, _TEST_USER_ID)
    else:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository, make_engine

        engine = make_engine(f"sqlite:///{path}")
        repo = SqlAlchemyMovieRepository(engine, _TEST_USER_ID)

    repo.init_schema()
    yield repo
    if engine is not None:
        engine.dispose()


@pytest.fixture
def repo(backend_repo):
    """A clean repository for each contract test, reset before use."""
    backend_repo.reset()
    backend_repo.ensure_user(_TEST_USER_ID, "test")
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
    from app.main import app, get_repository
    from app.storage.sqlite_repo import SqliteMovieRepository

    repo = SqliteMovieRepository(get_settings().movies_db_path, _TEST_USER_ID)
    repo.init_schema()
    repo.reset()
    repo.ensure_user(_TEST_USER_ID, "test")
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(params=["sqlite", "sqlalchemy"])
def two_owners(request, tmp_path):
    """A pair of repos bound to different users over one fresh db, for
    exercising the per-user ownership boundary on each backend."""
    db = str(tmp_path / "scoped.db")
    engine = None
    if request.param == "sqlite":
        from app.storage.sqlite_repo import SqliteMovieRepository

        alice = SqliteMovieRepository(db, 1)
        bob = SqliteMovieRepository(db, 2)
    else:
        from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository, make_engine

        engine = make_engine(f"sqlite:///{db}")
        alice = SqlAlchemyMovieRepository(engine, 1)
        bob = SqlAlchemyMovieRepository(engine, 2)

    alice.init_schema()
    alice.ensure_user(1, "alice")
    alice.ensure_user(2, "bob")
    yield alice, bob
    if engine is not None:
        engine.dispose()


@pytest.fixture
def identity_client():
    """No repo override, so full cookie -> user -> scoped repo path runs.
    Resets the schema and seeds users 1 and 2 on the shared SQLite backend."""
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app
    from app.storage.sqlite_repo import SqliteMovieRepository

    app.dependency_overrides.clear()
    admin = SqliteMovieRepository(get_settings().movies_db_path, 1)
    admin.init_schema()
    admin.reset()
    admin.ensure_user(1, "Alice")
    admin.ensure_user(2, "Bob")
    return TestClient(app)
