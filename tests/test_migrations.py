"""Guard against drift between the ORM models and the Alembic migrations.

If a model in app/storage/sqlalchemy_repo.py changes without a matching
migration, the schema produced by `alembic upgrade head` no longer matches
Base.metadata, and `just new-migration` would emit a fresh revision. This test
upgrades a clean Postgres to head and asserts autogenerate finds nothing — i.e.
the models and the committed migrations agree.

It uses its own throwaway container rather than the session-scoped `postgres_url`
fixture: it upgrades from an empty schema, which would clobber the tables the
contract tests build on that shared database.
"""

from app.config import get_settings


def test_migrations_match_models(monkeypatch):
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from testcontainers.postgres import PostgresContainer

    from alembic import command
    from app.storage.sqlalchemy_repo import Base, make_engine

    with PostgresContainer("postgres:17-alpine", driver="psycopg") as pg:
        url = pg.get_connection_url()
        # env.py reads the URL from app config; point it at this container.
        monkeypatch.setenv("MOVIES_BACKEND", "postgres")
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()

        engine = make_engine(url)
        try:
            command.upgrade(Config("alembic.ini"), "head")
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                diff = compare_metadata(context, Base.metadata)
        finally:
            engine.dispose()
            get_settings.cache_clear()

    assert diff == [], f"ORM models and migrations have drifted: {diff}"
