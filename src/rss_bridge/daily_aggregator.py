import os
import time
import logging
import json
import textwrap
import threading
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

import feedparser
from feedgen.feed import FeedGenerator
from google import genai
from tqdm import tqdm

from .content_extraction import extract_article

logger = logging.getLogger(__name__)


class DailyAggregator:
    cache_dir = Path("feed_caches/daily")
    _locks = {}
    _locks_lock = threading.Lock()

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-3-flash-preview"
        else:
            logger.warning(
                "GEMINI_API_KEY not found. Summarization will fall back to original RSS summaries."
            )
            self.client = None

    def _get_lock(self, url: str) -> threading.Lock:
        with self._locks_lock:
            if url not in self._locks:
                self._locks[url] = threading.Lock()
            return self._locks[url]

    def _get_cache_path(self, url: str) -> Path:
        sanitized_url = url.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{sanitized_url}_cache.json"

    def _load_cache(self, url: str) -> dict:
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache from {cache_path}: {e}")
        return {"articles": {}, "summaries": {}}

    def _save_cache(self, url: str, cache_data: dict):
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache to {cache_path}: {e}")

    def summarize_day_with_gemini(self, date: str, articles: list[dict]) -> str:
        if not self.client or not articles:
            return ""

        # Build context for Gemini
        context = [f"News from {date}:"]
        for a in articles:
            context.append(f"Title: {a['title']}\nContent: {a['content']}")

        full_day_text = "\n\n---\n\n".join(context)
        prompt = textwrap.dedent(f"""\
            You are an inquisitive journalist and world-class news analyst.
            Your goal is to provides a cohesive, insightful, and structured daily summary of the following news articles from {date}.

            Respond using ONLY the following structure:
            1. **General Overview**: Start with a high-level, engaging summary of the day's main themes and most critical events.
            2. **Topic Clusters**: Group similar or redundant articles into clearly defined topic clusters. For each cluster, provides a sharp, analytical summary that connects the related stories.

            Critical Instructions:
            - **Language Consistency**: ALL parts of your response, including headings, labels, and summaries, must be written in the SAME language as the input articles. For example, if the articles are in German, use German headings like "Allgemeiner Überblick" instead of "General Overview".
            - **Grounding**: ONLY use information from the provided news articles. Do NOT hallucinate or include external knowledge not present in the input text.
            - **Accuracy**: If an article does not contain enough information to summarize, skip it.

            Formatting Instructions:
            - Use ONLY simple HTML tags (e.g., <h3> for cluster titles, <p> for paragraphs, <ul>/<li> for lists).
            - Use <b> or <i> for emphasis if needed.
            - Do NOT use Markdown (no #, **, or - prefixes).

            Input Articles:
            {full_day_text}
        """)

        try:
            response = self.client.models.generate_content(
                model=self.model_id, contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini daily summarization failed: {e}")
            return ""

    def process_feed(self, url: str, num: int | None = None) -> str:
        logger.info(f"Processing daily aggregation for {url}")
        feed = feedparser.parse(url)

        if not feed.entries:
            logger.warning(f"No entries found in feed: {url}")
            return ""

        # We acquire a lock for this specific URL to prevent concurrent redundant processing
        # (e.g. when an RSS reader times out and retries immediately)
        with self._get_lock(url):
            # Load cache
            cache = self._load_cache(url)
            cache_updated = False

            # Group entries by day (YYYY-MM-DD), skipping today
            entries_by_day = defaultdict(list)
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            for entry in feed.entries:
                published_parsed = entry.get("published_parsed")
                if published_parsed:
                    date_str = time.strftime("%Y-%m-%d", published_parsed)
                else:
                    date_str = today_str

                if date_str == today_str:
                    logger.debug(f"Skipping entry from today: {entry.title}")
                    continue

                entries_by_day[date_str].append(entry)

            # Apply filtering based on 'num' parameter
            sorted_days = sorted(entries_by_day.keys(), reverse=True)

            if num is not None:
                if num > 0:
                    # Limit total number of articles across all days
                    filtered_entries_by_day = defaultdict(list)
                    count = 0
                    for date_str in sorted_days:
                        for entry in entries_by_day[date_str]:
                            if count < num:
                                filtered_entries_by_day[date_str].append(entry)
                                count += 1
                            else:
                                break
                        if count >= num:
                            break
                    entries_by_day = filtered_entries_by_day
                    sorted_days = sorted(entries_by_day.keys(), reverse=True)
                elif num < 0:
                    # Limit number of full days
                    days_to_keep = abs(num)
                    sorted_days = sorted_days[:days_to_keep]
                    entries_by_day = {d: entries_by_day[d] for d in sorted_days}

            if not sorted_days:
                logger.warning(f"No entries remaining after filtering for: {url}")
                return ""

            fg = FeedGenerator()
            fg.id(f"{url}/daily")
            fg.title(f"Daily Aggregated: {feed.feed.get('title', 'Unknown')}")
            fg.link(href=feed.feed.get("link", url), rel="alternate")
            fg.description(f"Daily summaries of {feed.feed.get('title', url)}")

            # Debug output: Summary of articles per day
            logger.info("Plan for aggregation:")
            for date_str in sorted_days:
                logger.info(f"  {date_str}: {len(entries_by_day[date_str])} articles")

            # Process each day
            for date_str in tqdm(sorted_days, desc="Processing days"):
                day_entries = entries_by_day[date_str]
                logger.info(f"Aggregating {len(day_entries)} entries for {date_str}")

                # Extract content for all articles of the day
                articles_to_summarize = []
                article_links_html = []
                article_urls = []
                day_has_new_content = False

                cached_count = 0
                for entry in tqdm(day_entries, desc=f"Day: {date_str}"):
                    article_url = entry.link
                    article_title = entry.title
                    article_urls.append(article_url)

                    if article_url in cache["articles"]:
                        cached_count += 1
                        full_content = cache["articles"][article_url]
                    else:
                        _, full_content = extract_article(article_url)
                        cache["articles"][article_url] = full_content
                        cache_updated = True
                        day_has_new_content = True

                content_for_summary = (
                    full_content if full_content else entry.get("summary", "")
                )

                articles_to_summarize.append(
                    {"title": article_title, "content": content_for_summary}
                )

                article_links_html.append(
                    f"<li><a href='{article_url}'>{article_title}</a></li>"
                )

            logger.info(
                f"Used cached content for {cached_count}/{len(day_entries)} entries"
            )

            # Generate single summary for the day
            summary_key = date_str

            # Check if we can reuse a cached summary
            if not day_has_new_content and summary_key in cache["summaries"]:
                logger.info(f"Using cached summary for {date_str}")
                daily_summary = cache["summaries"][summary_key]
            else:
                logger.info(
                    f"Generating new summary for {date_str} (new content: {day_has_new_content})"
                )
                daily_summary = self.summarize_day_with_gemini(
                    date_str, articles_to_summarize
                )
                if daily_summary:
                    cache["summaries"][summary_key] = daily_summary
                    cache_updated = True
                else:
                    # Provide a fallback for the current response but DO NOT flush it to the cache
                    # so that subsequent RSS updates will retry hitting Gemini for a proper summary.
                    daily_summary = "<em>Daily summary could not be generated.</em>"

            # Save incrementally after each day to preserve progress
            if cache_updated:
                self._save_cache(url, cache)
                cache_updated = False

            # Build final content
            full_description = daily_summary

            fe = fg.add_entry()
            fe.id(f"{url}/daily/{date_str}")
            fe.title(f"Heise Daily Summary: {date_str}")
            fe.description(full_description)
            fe.link(href=f"{url}/daily/{date_str}")
            # Use a timezone-aware datetime for pubDate (standard RSS 2.0 format)
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            fe.pubDate(dt.replace(hour=23, minute=59, second=59))

        return fg.rss_str(pretty=True).decode("utf-8")
