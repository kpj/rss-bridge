# rss-bridge

A bridge between your RSS reader and an RSS source which extracts full articles.

## Usage

Run the `rss-bridge` server:
```bash
$ uv run uvicorn rss_bridge.main:app --host 0.0.0.0 --port 8000
```

Use the following URL scheme to add feeds to your RSS reader:
```
<host>:8000/bridge/?source_url=<rss feed source url>
```

You can optionally append `&num=<x>` to only load the `x` most recent feed entries.

## Tests

Run all tests with:
```bash
$ uv run pytest
```
