from newspaper import Article
from readability import Document
import requests


def extract_using_newspaper(url: str) -> tuple[str, str]:
    article = Article(url)
    article.download()
    article.parse()

    return article.title.strip(), article.text.strip()


def extract_using_readability(url: str) -> tuple[str, str]:
    response = requests.get(url)
    doc = Document(response.text)

    return doc.short_title(), doc.summary()


def extract_article(url: str) -> tuple[str, str]:
    title, content = extract_using_newspaper(url)
    if content:
        return title, content

    title, content = extract_using_readability(url)
    if content:
        return title, content

    response = requests.get(url)
    return url, response.text.strip()


def main():
    url = "https://paulgraham.com/progbot.html"

    title, text = extract_article(url)
    print(f"| {title} |\n")
    print(text)


if __name__ == "__main__":
    main()
