"""End-to-end tests against a running Docker container.

Unlike the in-process TestClient suite, these hit the built image over real
HTTP. They're marked `e2e` and deselected from the default (coverage-gated)
run. Run them against a container listening on E2E_BASE_URL with:

    uv run pytest tests/e2e -m e2e --no-cov
"""

import os

import httpx
import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as c:
        yield c


@pytest.fixture
def created_movie(client):
    """Create a movie for a test to act on, then remove it afterward.

    The container keeps real state across tests, so each test that needs a
    pre-existing movie makes its own and cleans it up. Teardown tolerates a
    404 in case the test under test already deleted it.
    """
    movie = client.post("/movies", json={"title": "The Matrix", "year": 1999}).json()
    yield movie
    client.delete(f"/movies/{movie['id']}")


# ---- JSON API ----


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_returns_201_with_server_fields(client):
    response = client.post("/movies", json={"title": "Heat", "year": 1995})
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["title"] == "Heat"
    assert body["year"] == 1995
    assert body["status"] == "to_watch"
    assert "created_at" in body
    assert "updated_at" in body
    client.delete(f"/movies/{body['id']}")  # don't leak into other tests


def test_get_returns_created_movie(client, created_movie):
    response = client.get(f"/movies/{created_movie['id']}")
    assert response.status_code == 200
    assert response.json() == created_movie


def test_list_includes_created_movie(client, created_movie):
    response = client.get("/movies")
    assert response.status_code == 200
    ids = [m["id"] for m in response.json()]
    assert created_movie["id"] in ids


def test_update_changes_fields(client, created_movie):
    response = client.patch(
        f"/movies/{created_movie['id']}",
        json={"status": "watched", "rating": 9},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "watched"
    assert body["rating"] == 9
    assert body["title"] == "The Matrix"  # fields omitted from PATCH survive


def test_delete_then_get_returns_404(client):
    movie = client.post("/movies", json={"title": "Inception"}).json()
    assert client.delete(f"/movies/{movie['id']}").status_code == 204
    assert client.get(f"/movies/{movie['id']}").status_code == 404


def test_get_missing_returns_404(client):
    response = client.get("/movies/99999999")
    assert response.status_code == 404


# ---- HTMX API ----


def test_index_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Movie Watchlist" in response.text
    assert "add-movie-form" in response.text


def test_ui_create_renders_row(client):
    response = client.post("/ui/movies", data={"title": "Blade Runner", "year": 1982})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Blade Runner" in response.text
    # the form path created a real row; clean it up via the JSON API
    for movie in client.get("/movies").json():
        if movie["title"] == "Blade Runner":
            client.delete(f"/movies/{movie['id']}")


def test_static_asset_served(client):
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
