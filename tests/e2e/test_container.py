"""End-to-end tests against a running Docker container.

Unlike the in-process TestClient suite, these hit the built image over real
HTTP. They're marked `e2e` and deselected from the default run.
Run them against a container listening on E2E_BASE_URL with:

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


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
