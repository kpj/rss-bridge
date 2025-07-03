import time
import logging
from pathlib import Path

import feedparser
from feedgen.feed import FeedGenerator

from tqdm import tqdm

from .content_extraction import extract_article


class FeedBridge:
    logger = logging.getLogger(__name__)
    cache_dir = Path("feed_caches")

    def __init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, url, num: int | None = None):
        self.logger.warning(
            f"Parsing {'all' if num is None else num} entries from {url}"
        )

        cache_filename = self._generate_cache_filename(url)
        cached_entry_by_id = {}
        if cache_filename.exists():
            cache_source = feedparser.parse(cache_filename)
            for entry in cache_source["entries"]:
                cached_entry_by_id[entry["id"]] = entry

        source = feedparser.parse(url)

        fg = FeedGenerator()
        fg.id(url)
        fg.title(source["feed"]["title"])
        fg.link(source["feed"]["links"])
        fg.description(source["feed"]["subtitle"])

        all_entries = sorted(
            source["entries"],
            key=lambda x: x.get("published_parsed", time.gmtime(0)),
            reverse=True,
        )
        if num is not None:
            all_entries = all_entries[:num]

        num_cached_entries = 0
        for entry in tqdm(all_entries):
            article_url = entry["link"]
            article_title = entry["title"]
            article_links = entry["links"]
            article_date = entry.get("published")

            if article_url in cached_entry_by_id:
                self.logger.debug(f"Using cached content for {article_url}")
                num_cached_entries += 1

                cached_entry = cached_entry_by_id[article_url]
                content = cached_entry.description
            else:
                _, content = extract_article(article_url)

            fe = fg.add_entry()
            fe.id(article_url)
            fe.title(article_title)
            fe.description(content)
            fe.link(article_links)
            if article_date is not None:
                fe.pubDate(article_date)

        self.logger.warning(
            f"Used cached content for {num_cached_entries}/{len(all_entries)} entries"
        )

        fg.rss_file(cache_filename)
        return fg.rss_str(pretty=True)

    def _generate_cache_filename(self, url: str) -> Path:
        sanitized_url = url.replace("/", "_")
        return self.cache_dir / f"{sanitized_url}__cache.xml"


def main():
    url = "https://filipesilva.github.io/paulgraham-rss/feed.rss"

    fb = FeedBridge()
    fb.parse(url, num=3)


if __name__ == "__main__":
    main()
