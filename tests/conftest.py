"""Shared test bootstrap and fixtures."""

import os
import tempfile

import pytest


def pytest_configure(config):
    """Pin test config before app modules are imported.

    The suite runs on SQLite (the contract tests reach Postgres directly via
    testcontainers, not through settings). Env vars take precedence over the
    .env file in pydantic-settings, so forcing the backend here keeps the suite
    hermetic: a developer's .env selecting Postgres can't leak in and make tests
    depend on a running database.
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["MOVIES_DB_PATH"] = db_path
    os.environ["MOVIES_BACKEND"] = "sqlite"
    os.environ["SESSION_SECRET"] = "test-secret"
    os.environ.pop("DATABASE_URL", None)


_TEST_USER_ID = 1


@pytest.fixture(scope="session")
def postgres_url():
    """A throwaway Postgres in a container, started once per session.

    driver="psycopg" makes the URL use psycopg v3 (postgresql+psycopg://),
    matching the driver installed in PR 1; the default would be psycopg2.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:17-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session", params=["sqlite", "postgres"])
def backend_repo(request):
    """One repository per backend, constructed once. Drives the MovieRepository
    contract test, which asserts both backends honor the same behavior.

    The ORM backend runs against a real Postgres (the production target); the
    raw backend runs against SQLite. Per-test isolation comes from the `repo`
    fixture's reset(), not from rebuilding the database here.
    """
    from app.config import get_settings

    engine = None
    if request.param == "sqlite":
        from app.storage.sqlite_repo import SqliteMovieRepository

        repo = SqliteMovieRepository(get_settings().movies_db_path, _TEST_USER_ID)
    else:
        from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository, make_engine

        engine = make_engine(request.getfixturevalue("postgres_url"))
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


@pytest.fixture(params=["sqlite", "postgres"])
def two_owners(request, tmp_path):
    """A pair of repos bound to different users over one db, for exercising the
    per-user ownership boundary on each backend."""
    engine = None
    if request.param == "sqlite":
        from app.storage.sqlite_repo import SqliteMovieRepository

        db = str(tmp_path / "scoped.db")
        alice = SqliteMovieRepository(db, 1)
        bob = SqliteMovieRepository(db, 2)
    else:
        from app.storage.sqlalchemy_repo import SqlAlchemyMovieRepository, make_engine

        engine = make_engine(request.getfixturevalue("postgres_url"))
        alice = SqlAlchemyMovieRepository(engine, 1)
        bob = SqlAlchemyMovieRepository(engine, 2)

    alice.init_schema()
    if request.param == "postgres":
        # Shared session container: clear leftover rows from earlier tests.
        alice.reset()
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
