import concurrent.futures
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from feedgen.feed import FeedGenerator
from fastapi.testclient import TestClient

from rss_bridge.main import app


@pytest.fixture
def client():
    # Context manager is needed to activate lifespans.
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_extract_article(monkeypatch):
    """Mock content extraction (prevents outgoing HTTP requests for articles)"""
    def mock_extract(url):
        return ("Mocked Title", f"Mocked content for {url}")
    monkeypatch.setattr(
        "rss_bridge.daily_aggregator.extract_article", mock_extract
    )


@pytest.fixture
def mock_gemini_client(monkeypatch):
    """Mock Gemini API client and track mock generation calls."""
    class MockGenerateContentResponse:
        text = "<h2>Cluster 1</h2><p>Mocked daily summary from Gemini</p>"

    mock_generate = MagicMock()

    def slow_generate(*args, **kwargs):
        time.sleep(0.5)  # Simulate slow API call for concurrency tests
        return MockGenerateContentResponse()

    mock_generate.side_effect = slow_generate

    class MockModels:
        generate_content = mock_generate

    class MockClient:
        def __init__(self, api_key=None):
            self.api_key = api_key or "mocked"
            self.models = MockModels()

    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    monkeypatch.setattr("rss_bridge.daily_aggregator.genai.Client", MockClient)
    return mock_generate


@pytest.fixture
def daily_client(client, tmp_path, monkeypatch, mock_extract_article, mock_gemini_client):
    """Client configured with an isolated cached directory and mocked external requests for the DailyAggregator."""
    monkeypatch.setattr(
        "rss_bridge.daily_aggregator.DailyAggregator.cache_dir",
        tmp_path / "feed_caches_daily",
    )
    # Re-initialize the daily_aggregator on the app state to pick up mocked env/client
    from rss_bridge.daily_aggregator import DailyAggregator
    client.app.state.daily_aggregator = DailyAggregator()
    return client


@pytest.fixture
def dummy_feed_path(tmp_path):
    fg = FeedGenerator()
    fg.id("dummy")
    fg.title("Dummy Feed")
    fg.link(href="https://foo.daily")
    fg.description("News.")

    fe = fg.add_entry()
    fe.id("dummy_01")
    fe.title("Hello World")
    fe.link(href="https://foo.daily/1")
    fe.description("Update!")

    # Add a date from yesterday so it gets aggregated (today's entries are skipped)
    yesterday_dt = datetime.now(timezone.utc) - timedelta(days=1)
    fe.pubDate(yesterday_dt)

    rss_file = tmp_path / "daily_rss.xml"
    fg.rss_file(rss_file)
    return rss_file.as_posix()


def test_simple_serve(client, dummy_feed_path):
    response = client.get(f"/extract/?source_url={dummy_feed_path}")
    assert "Hello World" in response.text

    cached_response = client.get(f"/extract/?source_url={dummy_feed_path}")
    assert (
        "Hello World" in cached_response.text
    )  # Avoid exact string match due to lastBuildDate varying by second


def test_daily_summary(daily_client, dummy_feed_path):
    response = daily_client.get(f"/daily_summary/?source_url={dummy_feed_path}")
    assert response.status_code == 200
    assert "Mocked daily summary from Gemini" in response.text

    # Run a second time to test cached summary (should not hit the mock extract_article or Gemini again)
    cached_response = daily_client.get(f"/daily_summary/?source_url={dummy_feed_path}")
    assert cached_response.status_code == 200
    assert "Mocked daily summary from Gemini" in cached_response.text


def test_daily_summary_concurrency(daily_client, dummy_feed_path, mock_gemini_client):
    def make_request():
        return daily_client.get(f"/daily_summary/?source_url={dummy_feed_path}")

    # Launch 3 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(make_request) for _ in range(3)]
        responses = [f.result() for f in futures]

    for response in responses:
        assert response.status_code == 200
        assert "Mocked daily summary from Gemini" in response.text

    # The LLM should only be called exactly once, since the first request
    # gets the lock and populates the cache for the other two.
    assert mock_gemini_client.call_count == 1
