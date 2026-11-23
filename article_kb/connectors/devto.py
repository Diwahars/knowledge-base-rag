from article_kb.connectors.base import BaseConnector
from article_kb.models import Article
from article_kb.utils import canonicalize_url, stable_hash


class DevToConnector(BaseConnector):
    source_name = "devto"

    def discover(self, tag, config):
        per_page = int(config.get("per_page", 100))
        url = "https://dev.to/api/articles"
        response = self.session.get(
            url,
            params={"tag": tag, "per_page": min(per_page, 100)},
            timeout=25
        )
        response.raise_for_status()
        results = []

        for item in response.json():
            article_url = canonicalize_url(item.get("url"))
            if not article_url:
                continue
            tags = item.get("tag_list") or []
            results.append(Article(
                source=self.source_name,
                source_tag=tag,
                title=item.get("title") or "",
                author=(item.get("user") or {}).get("name") or "",
                url=article_url,
                published_at=item.get("published_at"),
                updated_at=item.get("edited_at"),
                description=item.get("description") or "",
                reading_time=item.get("reading_time_minutes"),
                tags=", ".join(tags),
                language=item.get("language"),
                content_hash=stable_hash(item.get("title"), article_url),
                discovery_method="devto_tag_api"
            ))
        return results
