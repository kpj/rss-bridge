import pytest
from feedgen.feed import FeedGenerator
from fastapi.testclient import TestClient

from ..main import app


@pytest.fixture
def client():
    # Context manager is needed to activate lifespans.
    with TestClient(app) as client:
        yield client


@pytest.fixture
def dummy_feed_path(tmp_path):
    fg = FeedGenerator()
    fg.id("dummy")
    fg.title("Dummy Feed")
    fg.link(href="https://foo.foo")
    fg.description("World shattering news.")

    fe = fg.add_entry()
    fe.id("dummy01")
    fe.title("Hello World")
    fe.link(href="https://foo.foo")
    fe.description("Did you know?")

    rss_file = tmp_path / "rss.xml"
    fg.rss_file(rss_file)
    return rss_file.as_posix()


def test_simple_serve(client, dummy_feed_path):
    response = client.get(f"/bridge/?source_url={dummy_feed_path}")
    assert "Hello World" in response.text
