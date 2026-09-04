#!/usr/bin/env python3
"""Parse Utah FORGE PDF reports into layout-aware page records.

Writes ``data/processed/pdf_pages.jsonl`` with markdown headings (``##``) and
tables. Re-run this after parser changes, then ``scripts/build_index.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from wellground.retrieval.pdf_parser import parse_pdf_corpus, write_pages_jsonl
from wellground.retrieval.well_catalog import WellCatalog

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WELLS_CSV = PROJECT_ROOT / "data/seed/wells.csv"

DEFAULT_PDF_DIRS = (
    PROJECT_ROOT / "data/raw/pdfs/daily_reports/extracted",
    PROJECT_ROOT / "data/raw/pdfs/inj_prod/16A",
    PROJECT_ROOT / "data/raw/pdfs/inj_prod/16B",
)

DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/pdf_pages.jsonl"
DEFAULT_CORPUS_ROOT = PROJECT_ROOT / "data/raw/pdfs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write JSON Lines output (default: data/processed/pdf_pages.jsonl)",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=DEFAULT_CORPUS_ROOT,
        help="Root used to build stable doc_id paths",
    )
    parser.add_argument(
        "--wells-csv",
        type=Path,
        default=DEFAULT_WELLS_CSV,
        help="Well registry used to tag documents (default: data/seed/wells.csv)",
    )
    parser.add_argument(
        "pdf_dirs",
        nargs="*",
        type=Path,
        help="Directories to scan (defaults to daily_reports + inj_prod)",
    )
    args = parser.parse_args()

    pdf_dirs = args.pdf_dirs or list(DEFAULT_PDF_DIRS)
    catalog = WellCatalog.from_csv(args.wells_csv)
    pages = parse_pdf_corpus(*pdf_dirs, corpus_root=args.corpus_root, catalog=catalog)

    if not pages:
        print("No PDF pages found. Check that data/raw/pdfs/ exists and contains PDFs.")
        return

    write_pages_jsonl(pages, args.output)

    pdf_count = len({page.source_path for page in pages})
    print(f"Parsed {pdf_count} PDFs -> {len(pages)} pages")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
