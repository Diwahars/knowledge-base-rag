from pathlib import Path
import pandas as pd
import re

# Same metadata columns as the original project. Full text is excluded.
EXPORT_COLUMNS = [
    "id", "source", "source_tag", "title", "author", "url",
    "published_at", "updated_at", "scraped_at", "description",
    "reading_time", "tags", "language", "content_hash",
    "discovery_method", "extraction_status"
]

# Excel does not allow these XML control characters.
ILLEGAL_EXCEL_CHARS = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)


def clean_excel_value(value):
    """Remove characters that openpyxl cannot write to Excel."""

    if isinstance(value, str):
        value = ILLEGAL_EXCEL_CHARS.sub("", value)

        # Excel cell text limit is 32,767 characters.
        value = value[:32767]

    return value

def export_articles(rows, export_dir):
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for col in EXPORT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[EXPORT_COLUMNS]
    csv_path = Path(export_dir) / "articles.csv"
    xlsx_path = Path(export_dir) / "articles.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
     # Sanitize only the Excel copy.
    excel_df = df.copy()

    excel_df = excel_df.apply(
        lambda column: column.map(clean_excel_value)
    )

    excel_df.to_excel(
        xlsx_path,
        index=False,
        engine="openpyxl"
    )

    print(f"CSV exported: {csv_path}")
    print(f"Excel exported: {xlsx_path}")

    return csv_path, xlsx_path
