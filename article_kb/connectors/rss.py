import xml.etree.ElementTree as ET
from article_kb.connectors.base import BaseConnector
from article_kb.models import Article
from article_kb.utils import clean_text, parse_date, canonicalize_url, stable_hash


class RSSConnector(BaseConnector):
    """RSS connector used for Substack, FAUN and configured generic feeds."""

    def discover(self, tag, config):
        feeds = config.get("feeds", [])
        print(f"Discovering articles for tag: {tag} from feeds: {feeds}")
        results = []
        for feed_url in feeds:
            try:
                response = self.session.get(feed_url, timeout=25)
                response.raise_for_status()
                print(f"Content-Type: {response.headers.get('Content-Type', '')} from config: {feed_url}")
                root = ET.fromstring(response.content)
                channel_items = root.findall(".//item")
                print(f"Found {len(channel_items)} items")
                # Basic Atom support
                if not channel_items:
                    atom_ns = "{http://www.w3.org/2005/Atom}"
                    channel_items = root.findall(f".//{atom_ns}entry")

                for item in channel_items:
                    title = clean_text(
                        item.findtext("title")
                        or item.findtext("{http://www.w3.org/2005/Atom}title")
                    )
                    link = item.findtext("link")
                    if not link:
                        atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                        if atom_link is not None:
                            link = atom_link.get("href")
                    link = canonicalize_url(link)
                    if not link:
                        continue

                    description = (
                        item.findtext("description")
                        or item.findtext("{http://www.w3.org/2005/Atom}summary")
                        or item.findtext("{http://www.w3.org/2005/Atom}content")
                        or ""
                    )
                    author = (
                        item.findtext("{http://purl.org/dc/elements/1.1/}creator")
                        or item.findtext("author")
                        or item.findtext("{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name")
                        or ""
                    )
                    published = (
                        item.findtext("pubDate")
                        or item.findtext("{http://www.w3.org/2005/Atom}published")
                        or item.findtext("{http://www.w3.org/2005/Atom}updated")
                    )
                    categories = [
                        clean_text(x.text or x.get("term", ""))
                        for x in item.findall("category")
                    ]
                    # Feed-based tag matching: keep entries whose category/title/summary
                    # mentions the requested tag. If no category metadata exists, keep
                    # the feed entries because the feed itself was configured for this tag.
                    searchable = " ".join([title, clean_text(description), " ".join(categories)]).lower()
                    if categories and tag.lower() not in searchable:
                        continue

                    results.append(Article(
                        source=config.get("source_name", "rss"),
                        source_tag=tag,
                        title=title,
                        author=clean_text(author),
                        url=link,
                        published_at=parse_date(published),
                        description=clean_text(description),
                        tags=", ".join(categories) if categories else tag,
                        content_hash=stable_hash(title, link, author),
                        discovery_method="configured_rss_feed"
                    ))
            except Exception as exc:
                self.logger.exception("RSS feed failed (%s): %s", feed_url, exc)
        return results
