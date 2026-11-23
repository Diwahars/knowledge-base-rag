import xml.etree.ElementTree as ET
from article_kb.connectors.base import BaseConnector
from article_kb.models import Article
from article_kb.utils import clean_text, parse_date, canonicalize_url, stable_hash


class MediumConnector(BaseConnector):
    source_name = "medium"

    def discover(self, tag, config):
        url = f"https://medium.com/feed/tag/{tag.replace(' ', '-')}"
        response = self.session.get(url, timeout=25)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        results = []

        for item in root.findall(".//item"):
            link = canonicalize_url(item.findtext("link"))
            if not link:
                continue
            title = clean_text(item.findtext("title"))
            creator = item.findtext("{http://purl.org/dc/elements/1.1/}creator") or ""
            description = clean_text(item.findtext("description"))
            published = parse_date(item.findtext("pubDate"))
            categories = [clean_text(x.text) for x in item.findall("category") if x.text]
            results.append(Article(
                source=self.source_name,
                source_tag=tag,
                title=title,
                author=creator,
                url=link,
                published_at=published,
                description=description,
                tags=", ".join(categories) if categories else tag,
                content_hash=stable_hash(title, link, creator),
                discovery_method="medium_rss_tag"
            ))
        return results
