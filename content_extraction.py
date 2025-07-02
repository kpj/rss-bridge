import requests
from readability import Document


def extract_article(url: str) -> tuple[str, str]:
    response = requests.get(url)
    doc = Document(response.text)

    return (doc.short_title(), doc.summary())
    # return (doc.title(), doc.content())


def main():
    url = "https://paulgraham.com/progbot.html"

    extract_article(url)


if __name__ == "__main__":
    main()
