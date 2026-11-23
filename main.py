import argparse
import json
from article_kb.runner import run


def main():
    parser = argparse.ArgumentParser(
        description="Collect article metadata from multiple publishing sources."
    )
    parser.add_argument("--config", default="config/sources.json")
    parser.add_argument("--db", default="data/articles.db")
    parser.add_argument("--export-dir", default="exports")
    parser.add_argument(
        "--sources",
        nargs="*",
        help="Optional source names, e.g. medium devto"
    )
    pdf_group = parser.add_mutually_exclusive_group()
    pdf_group.add_argument("--pdf", help="Import one PDF file")
    pdf_group.add_argument("--pdf-dir", help="Import all PDFs from a directory recursively")
    parser.add_argument("--pdf-only", action="store_true", help="Skip web-source crawling")
    parser.add_argument("--non-recursive", action="store_true", help="Only scan the selected folder, not subfolders")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    if not args.pdf_only:
        run(
            config=config,
            db_path=args.db,
            export_dir=args.export_dir,
            selected_sources=set(args.sources) if args.sources else None
        )

    if args.pdf or args.pdf_dir:
        import logging
        from article_kb.pdf_ingest import import_pdfs
        logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
        input_path = args.pdf or args.pdf_dir
        result = import_pdfs(
            input_path=input_path,
            db_path=args.db,
            export_dir=args.export_dir,
            logger=logging.getLogger("article_kb.pdf"),
            recursive=not args.non_recursive,
        )
        print("\nPDF import summary")
        for key, value in result.items():
            print(f"{key}: {value}")
    elif args.pdf_only:
        parser.error("--pdf-only requires either --pdf or --pdf-dir")


if __name__ == "__main__":
    main()
