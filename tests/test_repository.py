"""Contract tests for the MovieRepository protocol.

Every backend must satisfy these. Parametrized over both implementations via
the `repo` fixture, so conformance is verified identically on each.

These assert behavior, not input validation: invalid input can't be constructed
(Pydantic rejects it at the model boundary before it reaches the repository), so
validation is covered by the API tests in test_movies.py instead.
"""

from app.models import MovieCreate, MovieStatus, MovieUpdate


def test_create_returns_movie_with_id(repo):
    movie = repo.create(MovieCreate(title="The Matrix"))
    assert movie.id is not None
    assert movie.title == "The Matrix"
    assert movie.status == MovieStatus.TO_WATCH  # default applied


def test_create_persists_all_fields(repo):
    created = repo.create(
        MovieCreate(
            title="Inception",
            year=2010,
            status=MovieStatus.WATCHED,
            rating=9,
            notes="Dream layers",
        )
    )
    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.title == "Inception"
    assert fetched.year == 2010
    assert fetched.status == MovieStatus.WATCHED
    assert fetched.rating == 9
    assert fetched.notes == "Dream layers"


def test_create_sets_timestamps(repo):
    movie = repo.create(MovieCreate(title="Heat"))
    assert movie.created_at is not None
    assert movie.updated_at is not None


def test_get_missing_returns_none(repo):
    assert repo.get(999) is None


def test_list_all_empty_initially(repo):
    assert repo.list_all() == []


def test_list_all_returns_created(repo):
    repo.create(MovieCreate(title="A"))
    repo.create(MovieCreate(title="B"))
    movies = repo.list_all()
    assert len(movies) == 2
    assert {m.title for m in movies} == {"A", "B"}


def test_update_persists_changes(repo):
    movie = repo.create(MovieCreate(title="Old Title"))
    updated = repo.update(movie.id, MovieUpdate(title="New Title"))
    assert updated is not None
    assert updated.title == "New Title"
    assert repo.get(movie.id).title == "New Title"


def test_update_is_partial(repo):
    movie = repo.create(MovieCreate(title="Keep", rating=5))
    updated = repo.update(movie.id, MovieUpdate(rating=8))
    assert updated is not None
    assert updated.title == "Keep"  # omitted field left untouched
    assert updated.rating == 8


def test_update_missing_returns_none(repo):
    assert repo.update(999, MovieUpdate(title="X")) is None


def test_delete_removes(repo):
    movie = repo.create(MovieCreate(title="Gone"))
    assert repo.delete(movie.id) is True
    assert repo.get(movie.id) is None


def test_delete_missing_returns_false(repo):
    assert repo.delete(999) is False


def test_update_status(repo):
    movie = repo.create(MovieCreate(title="X"))  # defaults to to_watch
    updated = repo.update(movie.id, MovieUpdate(status=MovieStatus.WATCHED))
    assert updated is not None
    assert updated.status == MovieStatus.WATCHED
