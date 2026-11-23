import requests
import trafilatura
from bs4 import BeautifulSoup


def extract_article_text(session: requests.Session, url: str, logger):
    """Extract readable text from an ordinarily accessible article page."""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        text = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=True,
            include_links=False,
            favor_precision=True,
        )
        if text and text.strip():
            return text.strip(), "success"

        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            node.decompose()
        main = soup.find("article") or soup.find("main")
        if main:
            fallback = main.get_text("\\n", strip=True)
            if fallback:
                return fallback, "success_fallback"
        return None, "no_content"
    except requests.RequestException as exc:
        logger.warning("Article fetch failed for %s: %s", url, exc)
        return None, "fetch_failed"
    except Exception:
        logger.exception("Article extraction failed for %s", url)
        return None, "extraction_failed"
