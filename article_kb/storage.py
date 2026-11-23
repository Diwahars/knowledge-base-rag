import sqlite3
from pathlib import Path
from article_kb.utils import utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_tag TEXT,
    title TEXT NOT NULL,
    author TEXT,
    url TEXT NOT NULL,
    published_at TEXT,
    updated_at TEXT,
    scraped_at TEXT NOT NULL,
    description TEXT,
    content TEXT,
    reading_time INTEGER,
    tags TEXT,
    language TEXT,
    content_hash TEXT,
    discovery_method TEXT,
    extraction_status TEXT,
    page_count INTEGER,
    UNIQUE(source, url)
);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_tag ON articles(source_tag);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
"""

class SQLiteStorage:
    def __init__(self, db_path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = {r[1] for r in conn.execute("PRAGMA table_info(articles)")}
            if "content" not in columns:
                conn.execute("ALTER TABLE articles ADD COLUMN content TEXT")
            if "extraction_status" not in columns:
                conn.execute("ALTER TABLE articles ADD COLUMN extraction_status TEXT")
            if "page_count" not in columns:
                conn.execute("ALTER TABLE articles ADD COLUMN page_count INTEGER")

    def connect(self):
        return sqlite3.connect(self.db_path)

    def has_content(self, source, url):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT content FROM articles WHERE source=? AND url=?",
                (source, url)
            ).fetchone()
            return bool(row and row[0] and row[0].strip())

    def has_content_hash(self, source, content_hash):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM articles WHERE source=? AND content_hash=? LIMIT 1",
                (source, content_hash)
            ).fetchone()
            return row is not None

    def save_articles(self, articles):
        changed = 0
        with self.connect() as conn:
            for article in articles:
                data = article.to_dict()
                data["scraped_at"] = utc_now()
                cur = conn.execute("""
                    INSERT INTO articles (
                        source, source_tag, title, author, url, published_at,
                        updated_at, scraped_at, description, content, reading_time,
                        tags, language, content_hash, discovery_method, extraction_status, page_count
                    ) VALUES (
                        :source, :source_tag, :title, :author, :url, :published_at,
                        :updated_at, :scraped_at, :description, :content, :reading_time,
                        :tags, :language, :content_hash, :discovery_method, :extraction_status, :page_count
                    )
                    ON CONFLICT(source, url) DO UPDATE SET
                        content = CASE
                            WHEN excluded.content IS NOT NULL AND TRIM(excluded.content) != ''
                            THEN excluded.content ELSE articles.content END,
                        extraction_status = CASE
                            WHEN excluded.content IS NOT NULL AND TRIM(excluded.content) != ''
                            THEN excluded.extraction_status
                            ELSE COALESCE(articles.extraction_status, excluded.extraction_status)
                        END
                """, data)
                changed += max(cur.rowcount, 0)
        return changed

    def fetch_all(self):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(
                "SELECT * FROM articles ORDER BY published_at DESC, id DESC"
            ).fetchall()]

    def count(self):
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    def count_with_content(self):
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM articles WHERE content IS NOT NULL AND TRIM(content) != ''"
            ).fetchone()[0]
