"""SQLAlchemy 2.0 ORM implementation of the movie repository.

Same MovieRepository protocol as the stdlib sqlite3 backend
(app/storage/sqlite_repo.py), built on the ORM instead of raw SQL. Both
persist to a SQLite file; the difference is the access layer, not the
database.

init_schema()/reset() are lifecycle/test concerns, deliberately off the
protocol — same split as the sqlite backend.
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models import MovieCreate, MovieRead, MovieUpdate


class Base(DeclarativeBase):
    pass


class MovieORM(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    year: Mapped[int | None]
    status: Mapped[str]
    rating: Mapped[int | None]
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _now() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(dt: datetime) -> datetime:
    # SQLite has no native datetime type, so timezone might not persist
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _to_read(movie: MovieORM) -> MovieRead:
    # Here, we use Dict instead of model_validate(movie) to check for timezone
    return MovieRead.model_validate(
        {
            "id": movie.id,
            "title": movie.title,
            "year": movie.year,
            "status": movie.status,
            "rating": movie.rating,
            "notes": movie.notes,
            "created_at": _ensure_utc(movie.created_at),
            "updated_at": _ensure_utc(movie.updated_at),
        }
    )


class SqlAlchemyMovieRepository:
    """MovieRepository backed by the SQLAlchemy 2.0 ORM."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)

        # The engine is shared across FastAPI's threadpool, so same-thread is set False
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
        )
        self._sessions = sessionmaker(self._engine, expire_on_commit=False)

    # --- Lifescycle ---

    def init_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def reset(self) -> None:
        # drop + recreate also clears SQLite's autoincrement counter back to 1
        Base.metadata.drop_all(self._engine)
        Base.metadata.create_all(self._engine)

    def dispose(self) -> None:
        """Release the engine's connection pool. Lifecycle/shutdown concern."""
        self._engine.dispose()

    # --- MovieRepository protocol ---

    def create(self, data: MovieCreate) -> MovieRead:
        now = _now()
        movie = MovieORM(
            title=data.title,
            year=data.year,
            status=data.status.value,
            rating=data.rating,
            notes=data.notes,
            created_at=now,
            updated_at=now,
        )

        with self._sessions() as session:
            session.add(movie)
            session.commit()
            return _to_read(movie)

    def get(self, movie_id: int) -> MovieRead | None:
        with self._sessions() as session:
            movie = session.get(MovieORM, movie_id)
            return _to_read(movie) if movie is not None else None

    def list_all(self) -> list[MovieRead]:
        with self._sessions() as session:
            movies = session.scalars(select(MovieORM).order_by(MovieORM.id)).all()
            return [_to_read(m) for m in movies]

    def update(self, movie_id: int, data: MovieUpdate) -> MovieRead | None:
        changes = data.model_dump(exclude_unset=True)
        with self._sessions() as session:
            movie = session.get(MovieORM, movie_id)
            if movie is None:
                return None

            for field, value in changes.items():
                if field == "status" and value is not None:
                    value = value.value
                setattr(movie, field, value)
            movie.updated_at = _now()
            session.commit()
            return _to_read(movie)

    def delete(self, movie_id: int) -> bool:
        with self._sessions() as session:
            movie = session.get(MovieORM, movie_id)
            if movie is None:
                return False
            session.delete(movie)
            session.commit()
            return True
