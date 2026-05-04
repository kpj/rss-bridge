import os
from pathlib import Path

import pytest

from rss_bridge.daily_aggregator import DailyAggregator


@pytest.mark.live
def test_live_aggregation(tmp_path, monkeypatch):
    """
    Runs a live aggregation against a real RSS feed and Gemini API.
    Only runs if --run-live is passed to pytest.
    """
    # Ensure API key is present
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.fail(
            "GEMINI_API_KEY environment variable not set. Live test cannot proceed."
        )

    # Isolate cache for the test
    test_cache_dir = tmp_path / "live_test_cache"
    monkeypatch.setattr(DailyAggregator, "cache_dir", test_cache_dir)

    aggregator = DailyAggregator(api_key=api_key)

    # Use a real feed (Heise RSS)
    feed_url = "https://www.heise.de/rss/heise-atom.xml"

    print(f"\n\n{'=' * 20} LIVE TEST START {'=' * 20}")
    print(f"Target Feed: {feed_url}")
    print(f"Model ID:    {aggregator.model_id}")
    print(f"Cache Dir:   {test_cache_dir}")
    print(f"{'=' * 57}\n")

    # Process the feed.
    # num=-1 means process the last full day of news (excluding today).
    rss_output = aggregator.process_feed(feed_url, num=-1)

    assert rss_output
    assert "<title>Daily Aggregated:" in rss_output

    # Display the result for evaluation
    print("--- GENERATED RSS FEED (FULL) ---")
    print(rss_output)
    print(f"\n{'=' * 22} LIVE TEST END {'=' * 23}\n")
