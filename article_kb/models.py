from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Article:
    source: str
    source_tag: str
    title: str
    author: str
    url: str
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    reading_time: Optional[int] = None
    tags: Optional[str] = None
    language: Optional[str] = None
    content_hash: Optional[str] = None
    discovery_method: str = "tag"
    extraction_status: str = "pending"
    page_count: Optional[int] = None

    def to_dict(self):
        return asdict(self)
