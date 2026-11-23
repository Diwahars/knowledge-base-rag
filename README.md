# Article Knowledge Base

Multi-source article discovery and full-text collection.

## Storage
- SQLite `data/articles.db`: metadata and full extracted article body in the `content` column.
- CSV/Excel `exports/articles.csv` and `articles.xlsx`: metadata-only columns, unchanged from the previous export schema.
- Existing metadata-only databases are automatically migrated by adding the `content` column.

## Sources
Medium tag RSS and Dev.to tag API connectors are implemented. Substack, FAUN and generic sites use configured RSS/Atom feeds in `config/sources.json`. Medium is enabled by default.

## Install and run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
Run selected sources:
```bash
python main.py --sources medium
python main.py --sources medium devto
```

## Extraction
Trafilatura extracts readable article text, with a limited BeautifulSoup fallback. Pages requiring login, paywall access, CAPTCHA, or JavaScript rendering may not be extractable. The crawler does not bypass access controls. Existing rows without text are backfilled when rediscovered; rows that already have text are skipped.

Respect source terms, robots guidance, copyright restrictions and rate limits. Store/process article text only where you have permission.


## Import PDF files

PDFs are stored as records in the same `articles` table (`source='pdf'`). The complete extracted text is saved in `content`. CSV/Excel exports remain metadata-only and keep the same export columns.

Import one file:

```bash
python main.py --pdf "/path/to/research-paper.pdf" --pdf-only
```

Import every PDF in a folder and all subfolders:

```bash
python main.py --pdf-dir "/path/to/pdfs" --pdf-only
```

Scan only the selected folder (no subfolders):

```bash
python main.py --pdf-dir "/path/to/pdfs" --pdf-only --non-recursive
```

Run web collection and then import a PDF folder in one run by omitting `--pdf-only`:

```bash
python main.py --pdf-dir "/path/to/pdfs"
```

The importer uses SHA-256 to skip the same PDF if it is imported again, even if the file is renamed or moved. It extracts text from text-based PDFs using `pypdf`. Image-only/scanned PDFs are recorded with `scanned_pdf_ocr_required`; OCR is not included yet. Password-protected PDFs that cannot be opened with an empty password are skipped. The importer does not bypass document encryption or access restrictions.

The database adds `page_count`; this field is intentionally not added to CSV/Excel, so the existing export layout remains unchanged.
