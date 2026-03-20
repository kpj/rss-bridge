import logging
import requests
import trafilatura
from newspaper import Article
from readability import Document

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 10


def extract_using_trafilatura(html: str, url: str) -> tuple[str, str]:
    """Extract content using Trafilatura from pre-fetched HTML."""
    try:
        content = trafilatura.extract(html, include_comments=False, include_tables=True)
        if content:
            metadata = trafilatura.extract_metadata(html)
            title = metadata.title if metadata else ""
            return (title or "").strip(), content.strip()
    except Exception as e:
        logger.error(f"Trafilatura extraction failed for {url}: {e}")
    return "", ""


def extract_using_newspaper(html: str, url: str) -> tuple[str, str]:
    """Extract content using Newspaper3k from pre-fetched HTML."""
    try:
        article = Article("")
        article.download(input_html=html)
        article.parse()
        if article.text:
            return article.title.strip(), article.text.strip()
    except Exception as e:
        logger.error(f"Newspaper3k extraction failed for {url}: {e}")
    return "", ""


def extract_using_readability(html: str, url: str) -> tuple[str, str]:
    """Extract content using Readability from pre-fetched HTML."""
    try:
        doc = Document(html)
        content = doc.summary().strip()
        if content:
            return doc.short_title().strip(), content
    except Exception as e:
        logger.error(f"Readability extraction failed for {url}: {e}")
    return "", ""


def extract_article(url: str) -> tuple[str, str]:
    """Controller that fetches HTML once and tries multiple extraction engines."""
    logger.debug(f"Attempting unified extraction for: {url}")

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        html = response.text
    except Exception as e:
        logger.error(f"Failed to fetch content for {url}: {e}")
        return url, ""

    # Strategy: try each engine in order until one succeeds
    engines = [
        ("Trafilatura", extract_using_trafilatura),
        ("Newspaper3k", extract_using_newspaper),
        ("Readability", extract_using_readability),
    ]

    for name, engine_func in engines:
        title, content = engine_func(html, url)
        if content:
            logger.debug(f"Extraction successful using {name}")
            return title, content

    # Final Fallback: Raw HTML
    logger.debug("Falling back to raw HTML")
    return url, html.strip()


def main():
    url = "https://paulgraham.com/progbot.html"
    excerpt_length = 300

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    html = response.text

    print(f"--- Testing Individual Engines for {url} ---\n")

    print("1. Trafilatura:")
    title, text = extract_using_trafilatura(html, url)
    print(f"   Title: {title}")
    print(f"   Content: {text[:excerpt_length]}...\n")

    print("2. Newspaper3k:")
    title, text = extract_using_newspaper(html, url)
    print(f"   Title: {title}")
    print(f"   Content: {text[:excerpt_length]}...\n")

    print("3. Readability:")
    title, text = extract_using_readability(html, url)
    print(f"   Title: {title}")
    print(f"   Content: {text[:excerpt_length]}...\n")

    print("--- Testing Unified extract_article ---")
    title, text = extract_article(url)
    print(f"Final Selection Title: {title}")
    print(f"Final Selection Content: {text[:excerpt_length]}... ({len(text)} chars)")


if __name__ == "__main__":
    main()
