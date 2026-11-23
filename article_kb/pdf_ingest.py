"""Import text-based PDFs into the shared SQLite article table."""
from pathlib import Path
import hashlib
import logging

from pypdf import PdfReader

from article_kb.models import Article
from article_kb.storage import SQLiteStorage
from article_kb.utils import utc_now, stable_hash


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pdf_date(value):
    """Convert common PDF date metadata (D:YYYYMMDD...) to ISO text."""
    if not value:
        return None
    value = str(value).strip()
    if value.startswith("D:"):
        value = value[2:]
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}T00:00:00+00:00"
    return None


def extract_pdf(path: Path, logger: logging.Logger):
    """Return (article, status). Text is extracted page by page."""
    file_hash = sha256_file(path)
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception:
                unlocked = 0
            if not unlocked:
                return None, "encrypted_pdf"

        metadata = reader.metadata
        title = (getattr(metadata, "title", None) if metadata else None) or path.stem
        author = (getattr(metadata, "author", None) if metadata else None) or ""
        created = _pdf_date(getattr(metadata, "creation_date", None) if metadata else None)
        updated = _pdf_date(getattr(metadata, "modification_date", None) if metadata else None)

        page_texts = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_texts.append(page.extract_text() or "")
            except Exception as exc:
                logger.warning("Could not extract page %d from %s: %s", page_number, path, exc)
                page_texts.append("")

        content = "\n\n".join(text.strip() for text in page_texts if text.strip()).strip()
        page_count = len(reader.pages)
        status = "success" if content else "scanned_pdf_ocr_required"
        word_count = len(content.split())
        article = Article(
            source="pdf",
            source_tag="local_pdf",
            title=str(title).strip(),
            author=str(author).strip(),
            url=str(path.resolve()),
            published_at=created,
            updated_at=updated,
            description=f"Local PDF | {page_count} pages | {path.name}",
            content=content or None,
            reading_time=max(1, round(word_count / 200)) if word_count else None,
            tags="pdf, local_document",
            content_hash=file_hash,
            discovery_method="local_pdf_import",
            extraction_status=status,
            page_count=page_count,
        )
        return article, status
    except Exception as exc:
        logger.exception("PDF import failed for %s: %s", path, exc)
        return None, "invalid_or_unreadable_pdf"


def discover_pdfs(input_path: str, recursive: bool = True):
    path = Path(input_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"PDF input path does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Input file is not a PDF: {path}")
        return [path]
    iterator = path.rglob("*") if recursive else path.glob("*")
    return sorted(p for p in iterator if p.is_file() and p.suffix.lower() == ".pdf")


def import_pdfs(input_path: str, db_path: str, export_dir: str,
                logger=None, recursive: bool = True):
    logger = logger or logging.getLogger("article_kb.pdf")
    storage = SQLiteStorage(db_path)
    pdf_paths = discover_pdfs(input_path, recursive=recursive)

    imported = skipped = failed = 0
    for pdf_path in pdf_paths:
        try:
            file_hash = sha256_file(pdf_path)
            if storage.has_content_hash("pdf", file_hash):
                skipped += 1
                logger.info("Already imported (same file hash): %s", pdf_path)
                continue
            article, status = extract_pdf(pdf_path, logger)
            if article is None:
                failed += 1
                logger.warning("Skipped %s (%s)", pdf_path, status)
                continue
            storage.save_articles([article])
            if article.content:
                imported += 1
            else:
                failed += 1
            logger.info("PDF: %s | pages=%s | status=%s",
                        pdf_path, article.page_count, status)
        except Exception:
            failed += 1
            logger.exception("Could not process PDF: %s", pdf_path)

    # Regenerate the same metadata-only exports used by web article ingestion.
    from article_kb.export import export_articles
    csv_path, xlsx_path = export_articles(storage.fetch_all(), export_dir)
    return {
        "found": len(pdf_paths), "imported_with_text": imported,
        "skipped_duplicates": skipped, "failed_or_needs_ocr": failed,
        "csv_path": str(csv_path), "xlsx_path": str(xlsx_path),
    }
