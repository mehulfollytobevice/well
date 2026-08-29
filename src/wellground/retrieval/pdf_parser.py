"""Extract text and metadata from PDF reports."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

from wellground.retrieval.well_catalog import DEFAULT_WELLS_CSV, WellCatalog


@dataclass
class PdfPage:
    """One page of extracted text, ready for chunking or indexing."""

    doc_id: str
    title: str
    page: int
    text: str
    source_path: str
    well_ids: list[str]


def find_pdf_files(*roots: Path) -> list[Path]:
    """Return all PDF paths under the given directories, sorted by path."""
    pdfs: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        pdfs.extend(sorted(root.rglob("*.pdf")))
    return pdfs


def guess_well_ids(*texts: str, catalog: WellCatalog | None = None) -> list[str]:
    """Find well ids mentioned in filenames or page text.

    Uses ``wells.csv`` by default so the same logic works for any operator
    (Utah FORGE, Fervo, etc.) as long as the seed catalog is kept up to date.
    """
    if catalog is None:
        catalog = WellCatalog.from_csv(DEFAULT_WELLS_CSV)
    return catalog.find_in_text(*texts)


def make_doc_id(pdf_path: Path, corpus_root: Path) -> str:
    """Stable id for citations, e.g. daily_reports/extracted/report.pdf."""
    relative = pdf_path.relative_to(corpus_root)
    return str(relative.with_suffix("")).replace("\\", "/")


def clean_text(raw: str) -> str:
    """Collapse whitespace so chunks are easier to read."""
    return re.sub(r"\s+", " ", raw).strip()


def parse_pdf(
    pdf_path: Path,
    *,
    corpus_root: Path,
    catalog: WellCatalog | None = None,
) -> list[PdfPage]:
    """Extract every non-empty page from a single PDF."""
    if catalog is None:
        catalog = WellCatalog.from_csv(DEFAULT_WELLS_CSV)

    reader = PdfReader(str(pdf_path))
    doc_id = make_doc_id(pdf_path, corpus_root)
    title = pdf_path.stem
    file_wells = catalog.find_in_text(pdf_path.name)

    pages: list[PdfPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if not text:
            continue

        well_ids = catalog.find_in_text(pdf_path.name, text)
        if not well_ids and file_wells:
            well_ids = file_wells

        pages.append(
            PdfPage(
                doc_id=doc_id,
                title=title,
                page=index,
                text=text,
                source_path=str(pdf_path),
                well_ids=well_ids,
            )
        )

    return pages


def parse_pdf_corpus(
    *roots: Path,
    corpus_root: Path | None = None,
    catalog: WellCatalog | None = None,
) -> list[PdfPage]:
    """Parse all PDFs under the given roots."""
    existing_roots = [root for root in roots if root.is_dir()]
    if not existing_roots:
        return []

    if catalog is None:
        catalog = WellCatalog.from_csv(DEFAULT_WELLS_CSV)

    if corpus_root is None:
        corpus_root = _common_parent(existing_roots)

    all_pages: list[PdfPage] = []
    for pdf_path in find_pdf_files(*existing_roots):
        all_pages.extend(parse_pdf(pdf_path, corpus_root=corpus_root, catalog=catalog))
    return all_pages


def write_pages_jsonl(pages: list[PdfPage], output_path: Path) -> None:
    """Save parsed pages as JSON Lines for inspection or downstream chunking."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for page in pages:
            handle.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")


def _common_parent(roots: list[Path]) -> Path:
    """Pick a stable root for doc_id paths when multiple folders are scanned."""
    if len(roots) == 1:
        return roots[0]
    parts = [root.resolve().parts for root in roots]
    shared: list[str] = []
    for segment_group in zip(*parts, strict=False):
        if len(set(segment_group)) == 1:
            shared.append(segment_group[0])
        else:
            break
    if shared:
        return Path(*shared)
    return roots[0]
