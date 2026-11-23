import logging
import time
import requests
from article_kb.connectors.medium import MediumConnector
from article_kb.connectors.substack import SubstackConnector
from article_kb.connectors.devto import DevToConnector
from article_kb.connectors.rss import RSSConnector
from article_kb.extractor import extract_article_text
from article_kb.storage import SQLiteStorage
from article_kb.export import export_articles

def setup_logger():
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    return logging.getLogger("article_kb")

def run(config, db_path, export_dir, selected_sources=None):
    logger = setup_logger()
    session = requests.Session()
    session.verify = False
    session.headers.update({"User-Agent": "ArticleKnowledgeBase/0.2"})
    db = SQLiteStorage(db_path)
    connectors = {
        "medium": MediumConnector(session, logger),
        "devto": DevToConnector(session, logger),
      #  "substack": SubstackConnector(session, logger),
    }
    rss_sources = {"substack", "faun", "generic"}
    summary = []

    for source, source_cfg in config.get("sources", {}).items():
        if selected_sources and source not in selected_sources:
            continue
        if not source_cfg.get("enabled", False):
            continue
        connector = RSSConnector(session, logger) if source in rss_sources else connectors.get(source)
        if connector is None:
            logger.warning("No connector registered for source: %s", source)
            continue

        for tag in source_cfg.get("tags", []):
            try:
                cfg = dict(source_cfg)
                cfg["source_name"] = source
                articles = connector.discover(tag, cfg)
                extracted = 0
                for article in articles:
                    if db.has_content(article.source, article.url):
                        article.content = None
                        article.extraction_status = "already_stored"
                        continue
                    body, status = extract_article_text(session, article.url, logger)
                    article.content = body
                    article.extraction_status = status
                    extracted += int(bool(body))
                    time.sleep(float(source_cfg.get("request_delay_seconds", 1)))
                changed = db.save_articles(articles)
                summary.append((source, tag, len(articles), extracted, changed))
                logger.info("%s/%s: discovered=%d text_extracted=%d db_changes=%d",
                            source, tag, len(articles), extracted, changed)
            except Exception:
                logger.exception("Collection failed for source=%s tag=%s", source, tag)

    rows = db.fetch_all()
    csv_path, xlsx_path = export_articles(rows, export_dir)
    print("\\nCollection summary")
    for source, tag, found, extracted, changed in summary:
        print(f"{source:10} {tag:20} discovered={found:4} extracted={extracted:4} db_changes={changed:4}")
    print(f"Total articles in SQLite: {db.count()}")
    print(f"Articles with full text: {db.count_with_content()}")
    print(f"CSV metadata export: {csv_path}")
    print(f"Excel metadata export: {xlsx_path}")
