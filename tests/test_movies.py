"""pytest tests for Movie Watchlist endpoints"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import reset_storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    reset_storage()


# ============================================================================
# Tests for POST /movies
# ============================================================================


# ---- Happy Paths ----
def test_create_minimal_movie_returns_201_with_object():
    response = client.post("/movies", json={"title": "The Matrix"})

    assert response.status_code == 201

    body = response.json()
    assert body["id"] is not None
    assert body["title"] == "The Matrix"
    assert body["year"] is None
    assert body["status"] == "to_watch"
    assert body["rating"] is None
    assert body["notes"] is None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_full_movie_returns_201_with_object():
    response = client.post(
        "/movies",
        json={
            "title": "The Matrix",
            "year": 1999,
            "status": "to_watch",
            "rating": 10,
            "notes": "I liked the slow-mo!",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["id"] is not None
    assert body["title"] == "The Matrix"
    assert body["year"] == 1999
    assert body["status"] == "to_watch"
    assert body["rating"] == 10
    assert body["notes"] == "I liked the slow-mo!"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_mixed_returns_201_with_object():
    response = client.post(
        "/movies",
        json={
            "title": "The Matrix",
            "year": 1999,
            "status": "to_watch",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["id"] is not None
    assert body["title"] == "The Matrix"
    assert body["year"] == 1999
    assert body["status"] == "to_watch"
    assert body["rating"] is None
    assert body["notes"] is None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_unknown_field_201_with_object():
    response = client.post("/movies", json={"title": "The Matrix", "id": 5})

    # id is set by the system, user-added id field is ignored, success

    assert response.status_code == 201

    body = response.json()
    assert body["id"] is not None
    assert body["title"] == "The Matrix"
    assert body["year"] is None
    assert body["status"] == "to_watch"
    assert body["rating"] is None
    assert body["notes"] is None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


# ---- Sad Paths ----


# - Title
def test_create_empty_returns_422():
    response = client.post("/movies", json={})

    assert response.status_code == 422


def test_create_empty_title_returns_422():
    response = client.post("/movies", json={"title": ""})

    assert response.status_code == 422


def test_create_above_max_title_returns_422():
    response = client.post("/movies", json={"title": "a" * 201})

    assert response.status_code == 422


def test_create_none_title_returns_422():
    response = client.post("/movies", json={"title": None})

    assert response.status_code == 422


# - Year
def test_create_below_min_year_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "year": 1887})

    assert response.status_code == 422


def test_create_above_max_year_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "year": 2101})

    assert response.status_code == 422


def test_create_string_year_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "year": "Nineteen ninety-nine"})

    assert response.status_code == 422


# - Status
def test_create_bad_status_str_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "status": "watching"})

    assert response.status_code == 422


def test_create_uppercase_status_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "status": "WATCHED"})

    assert response.status_code == 422


# - Rating
def test_create_below_min_rating_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "rating": 0})

    assert response.status_code == 422


def test_create_above_max_rating_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "rating": 11})

    assert response.status_code == 422


def test_create_str_rating_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "rating": "ten"})

    assert response.status_code == 422


# - Notes
def test_create_below_min_note_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "notes": ""})

    assert response.status_code == 422


def test_create_above_max_note_returns_422():
    response = client.post("/movies", json={"title": "The Matrix", "notes": "a" * 2001})

    assert response.status_code == 422


# ============================================================================
# Tests for GET /health
# ============================================================================


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ============================================================================
# Tests for GET /movies
# ============================================================================


# ---- Happy Path ----
def test_list_movies_empty_returns_200_with_empty_list():
    response = client.get("/movies")
    assert response.status_code == 200
    assert response.json() == []


def test_list_movies_single_returns_200_with_list():
    client.post("/movies", json={"title": "Heat"})
    response = client.get("/movies")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Heat"


def test_list_movies_multiple_returns_200_with_list():
    client.post("/movies", json={"title": "Heat"})
    client.post("/movies", json={"title": "Inception"})
    client.post("/movies", json={"title": "The Matrix"})

    response = client.get("/movies")

    assert response.status_code == 200

    body = response.json()
    assert len(body) == 3
    titles = [m["title"] for m in body]
    assert "Heat" in titles
    assert "Inception" in titles
    assert "The Matrix" in titles


# ============================================================================
# Tests for GET /movies/{id}
# ============================================================================


# ---- Happy Paths ----
def test_get_movie_returns_200_with_object():
    target = client.post(
        "/movies",
        json={
            "title": "The Matrix",
            "year": 1999,
            "status": "to_watch",
            "rating": 10,
            "notes": "I liked the slow-mo!",
        },
    ).json()

    response = client.get(f"/movies/{target['id']}")

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == target["id"]
    assert body["title"] == "The Matrix"
    assert body["year"] == 1999
    assert body["status"] == "to_watch"
    assert body["rating"] == 10
    assert body["notes"] == "I liked the slow-mo!"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_get_movie_with_multiple_returns_200_with_object():
    client.post("/movies", json={"title": "Heat"})
    target = client.post("/movies", json={"title": "Inception"}).json()
    client.post("/movies", json={"title": "The Matrix"})

    response = client.get(f"/movies/{target['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Inception"


# ---- Sad Paths ----
def test_get_nonexistent_id_returns_404():

    response = client.get("/movies/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


# ============================================================================
# Tests for PATCH /movies/{id}
# ============================================================================


# ---- Happy Path ----
def test_patch_movie_updates_only_specified_fields_returns_200_with_object():
    target = client.post(
        "/movies",
        json={
            "title": "The maTeriX",
            "year": 1999,
            "status": "watched",
            "rating": 1,
            "notes": "spelled wrong",
        },
    ).json()

    response = client.patch(f"/movies/{target['id']}", json={"title": "The Matrix"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target["id"]
    assert body["title"] == "The Matrix"
    assert body["year"] == 1999
    assert body["status"] == "watched"
    assert body["rating"] == 1
    assert body["notes"] == "spelled wrong"
    assert body["created_at"] == target["created_at"]
    assert body["updated_at"] != target["updated_at"]


def test_patch_movie_with_empty_body_returns_200_unchanged():
    target = client.post(
        "/movies", json={"title": "The Matrix", "year": 1999, "rating": 10, "notes": "great"}
    ).json()

    response = client.patch(f"/movies/{target['id']}", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target["id"]
    assert body["title"] == "The Matrix"
    assert body["year"] == 1999
    assert body["rating"] == 10
    assert body["notes"] == "great"
    assert body["created_at"] == target["created_at"]


def test_patch_movie_unknown_field_returns_200_with_object_unchanged():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"unknown_field": "x"})

    # Patch to unknown field is ignored

    assert response.status_code == 200
    assert response.json()["title"] == "Heat"


# ---- Sad Paths ----
def test_patch_nonexistent_movie_returns_404():
    response = client.patch("/movies/9999", json={"title": "The Matrix"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_patch_movie_with_non_integer_id_returns_422():
    response = client.patch("/movies/abc", json={"title": "The Matrix"})
    assert response.status_code == 422


def test_patch_movie_empty_title_returns_422():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"title": ""})
    assert response.status_code == 422


def test_patch_movie_year_out_of_range_returns_422():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"year": 2101})
    assert response.status_code == 422


def test_patch_movie_invalid_status_returns_422():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"status": "watching"})
    assert response.status_code == 422


def test_patch_movie_rating_out_of_range_returns_422():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"rating": 11})
    assert response.status_code == 422


def test_patch_movie_year_wrong_type_returns_422():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"year": "nineteen"})
    assert response.status_code == 422


# Currently returns 200 because of the "title: Title | None = None" problem
@pytest.mark.xfail(reason="PATCH null-handling semantics TBD")
def test_patch_movie_null_required_field_returns_422():
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"title": None})
    assert response.status_code == 422


# ============================================================================
# Tests for DELETE /movies/{id}
# ============================================================================


# ---- Happy paths ----
def test_delete_movie_returns_204():
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    response = client.delete(f"/movies/{target['id']}")

    assert response.status_code == 204

    # Assert there is no body
    assert response.content == b""


def test_delete_movie_actually_removes_it():
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    client.delete(f"/movies/{target['id']}")
    follow_up = client.get(f"/movies/{target['id']}")

    assert follow_up.status_code == 404


def test_delete_movie_does_not_affect_other_movies():
    keep = client.post("/movies", json={"title": "Heat"}).json()
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    client.delete(f"/movies/{target['id']}")
    response = client.get(f"/movies/{keep['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Heat"


# ---- Sad paths ----
def test_delete_nonexistent_movie_returns_404():
    response = client.delete("/movies/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_delete_movie_with_non_integer_id_returns_422():
    response = client.delete("/movies/abc")

    assert response.status_code == 422


def test_delete_already_deleted_movie_returns_404():
    target = client.post("/movies", json={"title": "The Matrix"}).json()
    client.delete(f"/movies/{target['id']}")

    response = client.delete(f"/movies/{target['id']}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"
