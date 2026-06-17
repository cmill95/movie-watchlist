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

from sqlalchemy import DateTime, Engine, ForeignKey, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models import MovieCreate, MovieRead, MovieUpdate, User
from app.storage.base import DuplicateUserName


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class MovieORM(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
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
            "user_id": movie.user_id,
            "title": movie.title,
            "year": movie.year,
            "status": movie.status,
            "rating": movie.rating,
            "notes": movie.notes,
            "created_at": _ensure_utc(movie.created_at),
            "updated_at": _ensure_utc(movie.updated_at),
        }
    )


def make_engine(db_path: Path | str) -> Engine:
    return create_engine(
        f"sqlite:///{Path(db_path)}",
        connect_args={"check_same_thread": False},
    )


class SqlAlchemyMovieRepository:
    """MovieRepository backed by the SQLAlchemy 2.0 ORM."""

    def __init__(self, engine: Engine, user_id) -> None:
        self._user_id = user_id
        self._engine = engine
        self._sessions = sessionmaker(self._engine, expire_on_commit=False)

    # --- Lifescycle ---

    def init_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def reset(self) -> None:
        # drop + recreate also clears SQLite's autoincrement counter back to 1
        Base.metadata.drop_all(self._engine)
        Base.metadata.create_all(self._engine)

    def ensure_user(self, user_id: int, name: str) -> None:
        with self._sessions() as session:
            if session.get(UserORM, user_id) is None:
                session.add(UserORM(id=user_id, name=name))
                session.commit()

    def create_user(self, name: str) -> User:
        with self._sessions() as session:
            if session.scalar(select(UserORM).where(UserORM.name == name)) is not None:
                raise DuplicateUserName(name)
            user = UserORM(name=name)
            session.add(user)
            session.commit()
            return User.model_validate(user)

    def get_user(self, user_id: int) -> User | None:
        with self._sessions() as session:
            user = session.get(UserORM, user_id)
            return User.model_validate(user) if user is not None else None

    def rename_user(self, user_id: int, name: str) -> User | None:
        with self._sessions() as session:
            taken = session.scalar(
                select(UserORM).where(UserORM.name == name, UserORM.id != user_id)
            )
            if taken is not None:
                raise DuplicateUserName(name)
            user = session.get(UserORM, user_id)
            if user is None:
                return None
            user.name = name
            session.commit()
            return User.model_validate(user)

    def list_users(self) -> list[User]:
        with self._sessions() as session:
            users = session.scalars(select(UserORM).order_by(UserORM.id)).all()
            return [User.model_validate(user) for user in users]

    # --- MovieRepository protocol ---

    def create(self, data: MovieCreate) -> MovieRead:
        now = _now()
        movie = MovieORM(
            user_id=self._user_id,
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

    def _get_owned(self, session, movie_id: int) -> MovieORM | None:
        return session.scalars(
            select(MovieORM).where(
                MovieORM.id == movie_id,
                MovieORM.user_id == self._user_id,
            )
        ).one_or_none()

    def get(self, movie_id: int) -> MovieRead | None:
        with self._sessions() as session:
            movie = self._get_owned(session, movie_id)
            return _to_read(movie) if movie is not None else None

    def list_all(self) -> list[MovieRead]:
        with self._sessions() as session:
            movies = session.scalars(
                select(MovieORM).where(MovieORM.user_id == self._user_id).order_by(MovieORM.id)
            ).all()
            return [_to_read(m) for m in movies]

    def update(self, movie_id: int, data: MovieUpdate) -> MovieRead | None:
        changes = data.model_dump(exclude_unset=True)
        with self._sessions() as session:
            movie = self._get_owned(session, movie_id)
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
            movie = self._get_owned(session, movie_id)
            if movie is None:
                return False
            session.delete(movie)
            session.commit()
            return True
