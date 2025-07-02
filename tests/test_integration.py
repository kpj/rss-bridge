import pytest
from fastapi.testclient import TestClient

from ..main import app


@pytest.fixture
def client(tmp_path):
    # Context manager is needed to activate lifespans.
    with TestClient(app) as client:
        yield client


def test_simple_serve(client):
    response = client.get(
        "/bridge/?source_url=https://filipesilva.github.io/paulgraham-rss/feed.rss&num=3"
    )
    print(response)
    assert False
