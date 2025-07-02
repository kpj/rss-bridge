import time
import logging

import feedparser
from feedgen.feed import FeedGenerator

from tqdm import tqdm

from .content_extraction import extract_article


class FeedBridge:
    logger = logging.getLogger(__name__)

    def parse(self, url, num: int | None = None):
        self.logger.warning(
            f"Parsing {'all' if num is None else num} entries from {url}"
        )

        source = feedparser.parse(url)

        fg = FeedGenerator()
        fg.id("foo")
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

        for entry in tqdm(all_entries):
            article_url = entry["link"]
            article_title = entry["title"]
            article_links = entry["links"]
            article_date = entry.get("published")

            fe = fg.add_entry()
            _, content = extract_article(article_url)
            fe.id(article_url)
            fe.title(article_title)
            fe.description(content)
            fe.link(article_links)
            if article_date is not None:
                fe.pubDate(article_date)

        return fg.rss_str(pretty=True)

    def gen(self):
        fg = FeedGenerator()


def main():
    url = "https://filipesilva.github.io/paulgraham-rss/feed.rss"

    fb = FeedBridge()

    fb.parse(url)


if __name__ == "__main__":
    main()
