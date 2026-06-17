"""pytest tests for Movie Watchlist endpoints"""


# ============================================================================
# Tests for GET / (HTML)
# ============================================================================


# ---- Happy Paths ----
def test_index_empty_returns_200_with_html_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Movie Watchlist" in response.text
    assert "add-movie-form" in response.text


def test_index_with_movies_renders_them(client):
    client.post("/movies", json={"title": "The Matrix", "year": 1999})
    client.post("/movies", json={"title": "Inception"})

    response = client.get("/")

    assert response.status_code == 200
    assert "The Matrix" in response.text
    assert "1999" in response.text
    assert "Inception" in response.text


# ============================================================================
# Tests for GET /ui/movies/{id} (HTML)
# ============================================================================


# ---- Happy Paths ----
def test_ui_get_movie_returns_200_with_row_html(client):
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    response = client.get(f"/ui/movies/{target['id']}")

    assert response.status_code == 200
    assert str(target["id"]) in response.text
    assert "The Matrix" in response.text


def test_ui_get_movie_among_multiple_returns_200_with_row_html(client):
    client.post("/movies", json={"title": "Heat"})
    target = client.post("/movies", json={"title": "Inception"}).json()
    client.post("/movies", json={"title": "The Matrix"})

    response = client.get(f"/ui/movies/{target['id']}")

    assert response.status_code == 200
    assert "Inception" in response.text
    assert "Heat" not in response.text
    assert "The Matrix" not in response.text


# ---- Sad Paths ----
def test_ui_get_non_existent_movie_returns_404(client):
    response = client.get("/ui/movies/9999")

    assert response.status_code == 404
    assert "Movie not found" in response.text


# ============================================================================
# Tests for GET /ui/movies/{id}/edit (HTML)
# ============================================================================


# ---- Happy Paths ----
def test_ui_edit_movie_form_returns_200_with_form_html(client):
    target = client.post(
        "/movies",
        json={
            "title": "The Matrix",
            "year": 1999,
            "status": "watched",
            "rating": 10,
            "notes": "I liked the slow-mo!",
        },
    ).json()

    response = client.get(f"/ui/movies/{target['id']}/edit")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<input" in response.text  # response is the row-as-form fragment
    # All current values appear pre-filled in the form.
    assert "The Matrix" in response.text
    assert "1999" in response.text
    assert "10" in response.text
    assert "I liked the slow-mo!" in response.text


def test_ui_edit_movie_form_marks_current_status_selected(client):
    target = client.post("/movies", json={"title": "Heat", "status": "watched"}).json()

    response = client.get(f"/ui/movies/{target['id']}/edit")

    assert response.status_code == 200
    # The current status option is pre-selected in the dropdown.
    assert 'value="watched"' in response.text
    assert "selected" in response.text


# ---- Sad Paths ----
def test_ui_edit_nonexistent_movie_returns_404(client):
    response = client.get("/ui/movies/9999/edit")
    assert response.status_code == 404
    assert "Movie not found" in response.text


# ============================================================================
# Tests for POST /ui/movies (HTML)
# ============================================================================


# ---- Happy Paths ----
def test_ui_create_movie_returns_200_with_row_html(client):
    response = client.post(
        "/ui/movies",
        data={
            "title": "The Matrix",
            "year": "1999",
            "status": "watched",
            "rating": "9",
            "notes": "Keanu Reeves, Laurence Fishburne, and Carrie-Anne Moss",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "The Matrix" in response.text
    assert "1999" in response.text
    assert "<tr" in response.text  # response is a row fragment


def test_ui_create_movie_persists_to_storage(client):
    client.post("/ui/movies", data={"title": "The Matrix"})

    # Verify via the JSON list endpoint — orthogonal to the HTML route under test.
    movies = client.get("/movies").json()
    assert len(movies) == 1
    assert movies[0]["title"] == "The Matrix"


# ---- Sad Paths ----
def test_ui_create_movie_missing_title_returns_422(client):
    response = client.post("/ui/movies", data={"year": "1995"})
    assert response.status_code == 422


def test_ui_create_movie_invalid_year_returns_422(client):
    response = client.post("/ui/movies", data={"title": "The Matrix", "year": "1500"})
    assert response.status_code == 422


# ============================================================================
# Tests for PATCH /ui/movies/{id} (HTML form update)
# ============================================================================


# ---- Happy Paths ----
def test_ui_update_movie_returns_200_with_updated_row_html(client):
    target = client.post("/movies", json={"title": "The maTeriX"}).json()

    response = client.patch(
        f"/ui/movies/{target['id']}",
        data={
            "title": "The Matrix",
            "year": "1999",
            "status": "watched",
            "rating": "10",
            "notes": "I liked the slow-mo!",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<tr" in response.text  # response is the display-row fragment
    assert "The Matrix" in response.text
    assert "1999" in response.text


def test_ui_update_movie_persists_to_storage(client):
    target = client.post("/movies", json={"title": "The maTeriX"}).json()

    client.patch(
        f"/ui/movies/{target['id']}",
        data={"title": "The Matrix", "status": "watched"},
    )

    updated = client.get(f"/movies/{target['id']}").json()
    assert updated["title"] == "The Matrix"
    assert updated["status"] == "watched"


# ---- Sad Paths ----
def test_ui_update_nonexistent_movie_returns_404(client):
    response = client.patch(
        "/ui/movies/9999",
        data={"title": "The Matrix"},
    )
    assert response.status_code == 404


def test_ui_update_movie_missing_title_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/ui/movies/{target['id']}", data={"year": "1995"})
    assert response.status_code == 422


def test_ui_update_movie_invalid_year_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(
        f"/ui/movies/{target['id']}",
        data={"title": "Heat", "year": "1500"},
    )
    assert response.status_code == 422


def test_ui_update_movie_invalid_status_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(
        f"/ui/movies/{target['id']}",
        data={"title": "Heat", "status": "watching"},
    )
    assert response.status_code == 422


# ============================================================================
# Tests for DELETE /ui/movies/{id} (HTML)
# ============================================================================


# ---- Happy Paths ----
def test_ui_delete_movie_returns_200_with_empty_body(client):
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    response = client.delete(f"/ui/movies/{target['id']}")

    assert response.status_code == 200
    assert response.text == ""


def test_ui_delete_movie_removes_from_storage(client):
    target = client.post("/movies", json={"title": "Heat"}).json()

    client.delete(f"/ui/movies/{target['id']}")

    assert client.get(f"/movies/{target['id']}").status_code == 404


# ---- Sad Paths ----
def test_ui_delete_nonexistent_movie_returns_404(client):
    response = client.delete("/ui/movies/9999")
    assert response.status_code == 404


# ============================================================================
# Tests for GET /health (JSON)
# ============================================================================


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ============================================================================
# Tests for GET /movies (JSON)
# ============================================================================


# ---- Happy Path ----
def test_list_movies_empty_returns_200_with_empty_list(client):
    response = client.get("/movies")
    assert response.status_code == 200
    assert response.json() == []


def test_list_movies_single_returns_200_with_list(client):
    client.post("/movies", json={"title": "Heat"})
    response = client.get("/movies")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Heat"


def test_list_movies_multiple_returns_200_with_list(client):
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
# Tests for GET /movies/{id} (JSON)
# ============================================================================


# ---- Happy Paths ----
def test_get_movie_returns_200_with_object(client):
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


def test_get_movie_with_multiple_returns_200_with_object(client):
    client.post("/movies", json={"title": "Heat"})
    target = client.post("/movies", json={"title": "Inception"}).json()
    client.post("/movies", json={"title": "The Matrix"})

    response = client.get(f"/movies/{target['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Inception"


# ---- Sad Paths ----
def test_get_nonexistent_id_returns_404(client):

    response = client.get("/movies/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


# ============================================================================
# Tests for POST /movies (JSON)
# ============================================================================


# ---- Happy Paths ----
def test_create_minimal_movie_returns_201_with_object(client):
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


def test_create_full_movie_returns_201_with_object(client):
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


def test_create_mixed_returns_201_with_object(client):
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


def test_create_unknown_field_201_with_object(client):
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
def test_create_empty_returns_422(client):
    response = client.post("/movies", json={})

    assert response.status_code == 422


def test_create_empty_title_returns_422(client):
    response = client.post("/movies", json={"title": ""})

    assert response.status_code == 422


def test_create_above_max_title_returns_422(client):
    response = client.post("/movies", json={"title": "a" * 201})

    assert response.status_code == 422


def test_create_none_title_returns_422(client):
    response = client.post("/movies", json={"title": None})

    assert response.status_code == 422


# - Year
def test_create_below_min_year_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "year": 1887})

    assert response.status_code == 422


def test_create_above_max_year_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "year": 2101})

    assert response.status_code == 422


def test_create_string_year_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "year": "Nineteen ninety-nine"})

    assert response.status_code == 422


# - Status
def test_create_bad_status_str_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "status": "watching"})

    assert response.status_code == 422


def test_create_uppercase_status_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "status": "WATCHED"})

    assert response.status_code == 422


# - Rating
def test_create_below_min_rating_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "rating": 0})

    assert response.status_code == 422


def test_create_above_max_rating_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "rating": 11})

    assert response.status_code == 422


def test_create_str_rating_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "rating": "ten"})

    assert response.status_code == 422


# - Notes
def test_create_below_min_note_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "notes": ""})

    assert response.status_code == 422


def test_create_above_max_note_returns_422(client):
    response = client.post("/movies", json={"title": "The Matrix", "notes": "a" * 2001})

    assert response.status_code == 422


# ============================================================================
# Tests for PATCH /movies/{id} (JSON)
# ============================================================================


# ---- Happy Path ----
def test_patch_movie_updates_only_specified_fields_returns_200_with_object(client):
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


def test_patch_movie_with_empty_body_returns_200_unchanged(client):
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


def test_patch_movie_unknown_field_returns_200_with_object_unchanged(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"unknown_field": "x"})

    # Patch to unknown field is ignored

    assert response.status_code == 200
    assert response.json()["title"] == "Heat"


# ---- Sad Paths ----
def test_patch_nonexistent_movie_returns_404(client):
    response = client.patch("/movies/9999", json={"title": "The Matrix"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_patch_movie_with_non_integer_id_returns_422(client):
    response = client.patch("/movies/abc", json={"title": "The Matrix"})
    assert response.status_code == 422


def test_patch_movie_empty_title_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"title": ""})
    assert response.status_code == 422


def test_patch_movie_year_out_of_range_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"year": 2101})
    assert response.status_code == 422


def test_patch_movie_invalid_status_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"status": "watching"})
    assert response.status_code == 422


def test_patch_movie_rating_out_of_range_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"rating": 11})
    assert response.status_code == 422


def test_patch_movie_year_wrong_type_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"year": "nineteen"})
    assert response.status_code == 422


# Currently returns 200 because of the "title: Title | None = None" problem
# @pytest.mark.xfail(reason="PATCH null-handling semantics TBD")
def test_patch_movie_null_required_field_returns_422(client):
    target = client.post("/movies", json={"title": "Heat"}).json()
    response = client.patch(f"/movies/{target['id']}", json={"title": None})
    assert response.status_code == 422


# ============================================================================
# Tests for DELETE /movies/{id} (JSON)
# ============================================================================


# ---- Happy paths ----
def test_delete_movie_returns_204(client):
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    response = client.delete(f"/movies/{target['id']}")

    assert response.status_code == 204

    # Assert there is no body
    assert response.content == b""


def test_delete_movie_actually_removes_it(client):
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    client.delete(f"/movies/{target['id']}")
    follow_up = client.get(f"/movies/{target['id']}")

    assert follow_up.status_code == 404


def test_delete_movie_does_not_affect_other_movies(client):
    keep = client.post("/movies", json={"title": "Heat"}).json()
    target = client.post("/movies", json={"title": "The Matrix"}).json()

    client.delete(f"/movies/{target['id']}")
    response = client.get(f"/movies/{keep['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Heat"


# ---- Sad paths ----
def test_delete_nonexistent_movie_returns_404(client):
    response = client.delete("/movies/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_delete_movie_with_non_integer_id_returns_422(client):
    response = client.delete("/movies/abc")

    assert response.status_code == 422


def test_delete_already_deleted_movie_returns_404(client):
    target = client.post("/movies", json={"title": "The Matrix"}).json()
    client.delete(f"/movies/{target['id']}")

    response = client.delete(f"/movies/{target['id']}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


# ============================================================================
# Tests for per-user identity (cookie -> current user)
# ============================================================================


def test_no_cookie_uses_default_user(identity_client):
    # POST with no cookie -> get_current_user falls back to the default user (1),
    # which owns the movie, so the same default-user request can read it back.
    created = identity_client.post("/movies", json={"title": "Default's"}).json()
    assert identity_client.get(f"/movies/{created['id']}").status_code == 200


def test_invalid_cookie_falls_back_to_default_user(identity_client):
    created = identity_client.post("/movies", json={"title": "Default's"}).json()
    resp = identity_client.get(
        f"/movies/{created['id']}", headers={"Cookie": "user_id=not-a-number"}
    )
    assert resp.status_code == 200


# ============================================================================
# Tests for application lifespan
# ============================================================================


def test_lifespan_initializes_storage():
    """Entering the app context runs lifespan: init_storage on startup,
    dispose_engine on shutdown."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


# ============================================================================
# Tests for mutliple users
# ============================================================================


def test_switch_user_sets_cookie_and_redirects(identity_client):
    resp = identity_client.post("/ui/switch-user", data={"user_id": "2"})
    assert resp.headers["HX-Redirect"] == "/"
    assert resp.cookies.get("user_id") == "2"


def test_index_renders_user_switcher(identity_client):
    html = identity_client.get("/").text  # no cookie -> default user 1 (alice)
    assert "Alice" in html
    assert "Bob" in html
    assert 'value="1" selected' in html


def test_index_renders_add_user_form(identity_client):
    html = identity_client.get("/").text
    assert 'hx-post="/ui/users"' in html
    assert 'name="name"' in html


def test_add_user_creates_and_switches_to_them(identity_client):
    resp = identity_client.post("/ui/users", data={"name": "Dana"})
    assert resp.headers["HX-Redirect"] == "/"
    new_id = resp.cookies.get("user_id")
    assert new_id is not None
    # The new user is now selectable in the switcher.
    assert "Dana" in identity_client.get("/").text


def test_add_user_trims_and_requires_a_name(identity_client):
    assert identity_client.post("/ui/users", data={"name": ""}).status_code == 422
    assert identity_client.post("/ui/users", data={"name": "   "}).status_code == 422
