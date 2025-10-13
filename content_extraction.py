from newspaper import Article


def extract_article(url: str) -> tuple[str, str]:
    article = Article(url)
    article.download()
    article.parse()

    return (article.title.strip(), article.text.strip())


def main():
    url = "https://paulgraham.com/progbot.html"

    title, text = extract_article(url)
    print(f"| {title} |\n")
    print(text)


if __name__ == "__main__":
    main()
