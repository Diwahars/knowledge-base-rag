import xml.etree.ElementTree as ET
from article_kb.connectors.base import BaseConnector
from article_kb.models import Article
from article_kb.utils import clean_text, parse_date, canonicalize_url, stable_hash


class SubstackConnector(BaseConnector):
    source_name = "substack"

    def discover(self, tag, config):
        url = f"https://medium.com/feed/tag/{tag.replace(' ', '-')}"
        response = self.session.get(url, timeout=25)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        results = []