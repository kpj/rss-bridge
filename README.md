# rss-bridge

A bridge between your RSS reader and an RSS source which extracts full articles.

## Usage

Run the `rss-bridge` server:

```bash
uv run uvicorn rss_bridge.main:app --host 0.0.0.0 --port 8000
```

### Full Article Extraction

Use the following URL scheme to add feeds to your RSS reader and extract full article texts:

```bash
<host>:8000/extract/?source_url=<rss feed source url>
```

You can optionally append `&num=<x>` to only load the `x` most recent feed entries.

### Daily LLM Summarizations

To aggregate all news of a day into a single digest, use the daily summary endpoint. This will extract all articles and use Gemini to generate a summary. (Requires `GEMINI_API_KEY` in your environment).

```bash
<host>:8000/daily_summary/?source_url=<rss feed source url>
```

You can optionally append `&num=-<x>` to only aggregate the `<x>` most recent full days. A positive `&num=<x>` instead restricts the total number of articles processed across all days.

## Tests

Run all tests with:

```bash
uv run pytest
```
