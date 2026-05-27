"""Storage-layer unit tests.

These tests bypass the HTTP routes and Pydantic models entirely, exercising
app.storage directly. They cover defense-in-depth guarantees that the
integration tests in test_movies.py only cover transitively.
"""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.models import MovieCreate, MovieUpdate
from app.storage import _UPDATABLE_COLUMNS, _connect, create, init_db, reset_storage


def _raw_insert(title="The Matrix", year=1999, status="to_watch", rating=None, notes=None):
    """Insert directly via SQL, bypassing Pydantic. For testing CHECK constraints.

    Returns the cursor or raises sqlite3.IntegrityError on constraint violation.
    Caller supplies the field they want to test with an invalid value; the
    other fields default to valid values.
    """
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        return conn.execute(
            """
            INSERT INTO movies (title, year, status, rating, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, year, status, rating, notes, now, now),
        )


# ============================================================================
# Tests for CHECK constraints
# ============================================================================


def test_raw_insert_with_valid_data_succeeds():
    _raw_insert(status="watched", rating=10, notes="Loved the slow-mo!")


def test_title_too_long_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(title="a" * 201)
    assert "title" in str(exc_info.value).lower()


def test_no_title_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(title="")
    assert "title" in str(exc_info.value).lower()


def test_below_min_year_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(year=1887)
    assert "year" in str(exc_info.value).lower()


def test_above_max_year_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(year=2101)
    assert "year" in str(exc_info.value).lower()


def test_invalid_status_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(status="favorites")  # Only to_watch and watched are valid
    assert "status" in str(exc_info.value).lower()


def test_note_below_min_length_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(notes="")
    assert "notes" in str(exc_info.value).lower()


def test_note_above_max_length_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(notes="a" * 2001)
    assert "notes" in str(exc_info.value).lower()


def test_rating_below_min_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(rating=0)
    assert "rating" in str(exc_info.value).lower()


def test_rating_above_max_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        _raw_insert(rating=11)
    assert "rating" in str(exc_info.value).lower()


# ============================================================================
# Tests for init_db() Idempotency
# ============================================================================


def test_init_db_is_idempotent():

    # If not idempotent, SQL will raise OperationalError: table movies already exists
    init_db()
    init_db()


# ============================================================================
# Tests for reset_storage()
# ============================================================================


def test_reset_storage_resets_id_sequence():
    first = create(MovieCreate(title="First"))
    assert first.id == 1

    reset_storage()

    second = create(MovieCreate(title="Second"))
    assert second.id == 1


# ============================================================================
# Tests for _UPDATEABLE_COLUMNS
# ============================================================================


def test_updatable_columns_matches_movie_update_fields():
    assert set(MovieUpdate.model_fields) == _UPDATABLE_COLUMNS
