"""SQLAlchemy 2.0 ORM implementation of the movie repository.

Same MovieRepository protocol as the stdlib sqlite3 backend
(app/storage/sqlite_repo.py), built on the ORM instead of raw SQL. The engine
URL decides the database: SQLite for local/dev, Postgres in production.

init_schema()/reset() are lifecycle/test concerns, deliberately off the
protocol — same split as the sqlite backend.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, ForeignKey, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.models import MovieCreate, MovieRead, MovieUpdate, User
from app.storage.base import DuplicateUserName


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    password_hash: Mapped[str | None] = mapped_column(default=None)


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


def _to_user(user: UserORM) -> User:
    return User(id=user.id, name=user.name, has_password=user.password_hash is not None)


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


def make_engine(url: str) -> Engine:
    # check_same_thread is a sqlite3-only connect arg (needed because FastAPI
    # serves across threads); psycopg has no such parameter and would reject it.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


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
                session.flush()  # make the row visible to the sequence sync below
                self._sync_user_id_seq(session)
                session.commit()

    def _sync_user_id_seq(self, session) -> None:
        """Advance the users id sequence past any explicitly-inserted id.

        Postgres does not bump the identity sequence when a row is inserted with
        an explicit id, so a later auto-id insert (create_user) would reuse that
        id and collide. SQLite has no such sequence; this is a no-op there.
        """
        if self._engine.dialect.name != "postgresql":
            return
        session.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT MAX(id) FROM users))"
            )
        )

    def create_user(self, name: str, password_hash: str | None = None) -> User:
        with self._sessions() as session:
            if session.scalar(select(UserORM).where(UserORM.name == name)) is not None:
                raise DuplicateUserName(name)
            user = UserORM(name=name, password_hash=password_hash)
            session.add(user)
            session.commit()
            return _to_user(user)

    def get_user(self, user_id: int) -> User | None:
        with self._sessions() as session:
            user = session.get(UserORM, user_id)
            return _to_user(user) if user is not None else None

    def get_password_hash(self, user_id: int) -> str | None:
        """The stored bcrypt hash, or None if the user is password-less/absent.

        Callers must not treat a None return as 'user exists but no password'
        without a separate existence check; here both collapse to None because
        only switch_user uses this, and it has already confirmed the user."""
        with self._sessions() as session:
            user = session.get(UserORM, user_id)
            return user.password_hash if user is not None else None

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
            return _to_user(user)

    def list_users(self) -> list[User]:
        with self._sessions() as session:
            users = session.scalars(select(UserORM).order_by(UserORM.id)).all()
            return [_to_user(user) for user in users]

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
