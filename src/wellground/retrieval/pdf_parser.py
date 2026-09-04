"""Extract text and metadata from PDF reports."""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pdfplumber  # type: ignore[import-untyped]
from pypdf import PdfReader

from wellground.retrieval.well_catalog import DEFAULT_WELLS_CSV, WellCatalog

KNOWN_HEADINGS: tuple[str, ...] = (
    "Current Operations",
    "Planned Operations",
    "Safety Summary",
    "Operations Summary",
    "Management Summary",
    "Bulk Inventory",
    "Safety Information",
    "Weather Information",
    "Wellsite Supervisors",
)

_KNOWN_HEADING_NEEDLES: tuple[tuple[str, str], ...] = tuple(
    sorted(
        ((heading, heading.lower()) for heading in KNOWN_HEADINGS),
        key=lambda item: -len(item[1]),
    )
)

HEADING_MAX_CHARS = 60
_LINE_Y_TOLERANCE = 3.0
_TABLE_PAD = 2.0


@dataclass
class PdfPage:
    """One page of extracted text, ready for chunking or indexing."""

    doc_id: str
    title: str
    page: int
    text: str
    source_path: str
    well_ids: list[str]


@dataclass(frozen=True)
class LayoutBlock:
    """One text line or markdown table, ordered from the top of the page."""

    top: float
    kind: str
    text: str
    font_size: float = 0.0


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
    """Normalize spaces within lines; keep line breaks for section layout."""
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in raw.splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def table_to_markdown(rows: list[list[str | None]] | None) -> str:
    """Serialize a grid of cells as a GitHub-flavored markdown table."""
    if not rows:
        return ""

    cleaned: list[list[str]] = []
    for row in rows:
        if row is None:
            continue
        cells = [re.sub(r"\s+", " ", (cell or "")).strip() for cell in row]
        if any(cells):
            cleaned.append(cells)
    if not cleaned:
        return ""

    width = max(len(row) for row in cleaned)
    if width < 2 and len(cleaned) < 2:
        return ""
    for row in cleaned:
        if len(row) < width:
            row.extend([""] * (width - len(row)))

    header = cleaned[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in cleaned[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def match_known_heading(line: str) -> str | None:
    """Return a canonical daily-report heading if ``line`` starts with one."""
    stripped = clean_text(line).rstrip(":").strip()
    if not stripped:
        return None
    lower = stripped.lower()
    for canonical, needle in _KNOWN_HEADING_NEEDLES:
        if lower == needle or lower.startswith(f"{needle} ") or lower.startswith(f"{needle}:"):
            return canonical
    return None


def is_generic_heading(line: str, *, font_size: float, median_size: float) -> bool:
    """True for short, larger-font or all-caps titles (SLB-style reports)."""
    stripped = clean_text(line).rstrip(":").strip()
    if not stripped or stripped.startswith("|") or stripped.startswith("##"):
        return False
    if match_known_heading(stripped):
        return True
    if len(stripped) > HEADING_MAX_CHARS:
        return False
    words = stripped.split()
    if not (1 <= len(words) <= 8):
        return False
    if sum(ch.isdigit() for ch in stripped) > 4:
        return False
    large = median_size > 0 and font_size >= median_size * 1.15
    all_caps = (
        stripped.isupper()
        and any(ch.isalpha() for ch in stripped)
        and (len(words) >= 2 or len(stripped) >= 8)
    )
    return bool(large or all_caps)


def heading_for_line(line: str, *, font_size: float, median_size: float) -> str | None:
    """Return the section title if this line should start a new section."""
    known = match_known_heading(line)
    if known:
        return known
    if is_generic_heading(line, font_size=font_size, median_size=median_size):
        return clean_text(line).rstrip(":").strip()
    return None


def render_layout_blocks(blocks: list[LayoutBlock]) -> str:
    """Turn ordered layout blocks into markdown with ``##`` section headings."""
    line_sizes = [
        block.font_size for block in blocks if block.kind == "line" and block.font_size > 0
    ]
    median_size = statistics.median(line_sizes) if line_sizes else 0.0

    output: list[str] = []
    saw_heading = False
    for block in sorted(blocks, key=lambda item: (item.top, item.kind != "line")):
        text = block.text.strip()
        if not text:
            continue
        if block.kind == "table":
            output.append(text)
            continue
        heading = heading_for_line(text, font_size=block.font_size, median_size=median_size)
        if heading:
            if output and not saw_heading:
                output.insert(0, "## Header")
            output.append(f"## {heading}")
            saw_heading = True
        else:
            output.append(text)

    rendered = "\n\n".join(output).strip()
    if not rendered:
        return ""
    if not saw_heading:
        return f"## Body\n{rendered}"
    if not rendered.startswith("## "):
        return f"## Header\n{rendered}"
    return rendered


def extract_page_layout(page: Any) -> str:
    """Build layout-aware markdown for one pdfplumber page."""
    blocks = _layout_blocks_from_page(page)
    if blocks:
        return render_layout_blocks(blocks)
    fallback = clean_text(page.extract_text() or "")
    if not fallback:
        return ""
    return f"## Body\n{fallback}"


def parse_pdf(
    pdf_path: Path,
    *,
    corpus_root: Path,
    catalog: WellCatalog | None = None,
) -> list[PdfPage]:
    """Extract every non-empty page from a single PDF."""
    if catalog is None:
        catalog = WellCatalog.from_csv(DEFAULT_WELLS_CSV)

    doc_id = make_doc_id(pdf_path, corpus_root)
    title = pdf_path.stem
    file_wells = catalog.find_in_text(pdf_path.name)

    try:
        pages = _parse_with_pdfplumber(
            pdf_path,
            doc_id=doc_id,
            title=title,
            file_wells=file_wells,
            catalog=catalog,
        )
    except Exception:
        pages = _parse_with_pypdf(
            pdf_path,
            doc_id=doc_id,
            title=title,
            file_wells=file_wells,
            catalog=catalog,
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


def _parse_with_pdfplumber(
    pdf_path: Path,
    *,
    doc_id: str,
    title: str,
    file_wells: list[str],
    catalog: WellCatalog,
) -> list[PdfPage]:
    pages: list[PdfPage] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            try:
                text = extract_page_layout(page)
            except Exception:
                text = clean_text(page.extract_text() or "")
                if text and not text.startswith("## "):
                    text = f"## Body\n{text}"
            if not text:
                continue
            pages.append(
                _page_record(
                    doc_id=doc_id,
                    title=title,
                    page=index,
                    text=text,
                    source_path=str(pdf_path),
                    file_wells=file_wells,
                    catalog=catalog,
                )
            )
    return pages


def _parse_with_pypdf(
    pdf_path: Path,
    *,
    doc_id: str,
    title: str,
    file_wells: list[str],
    catalog: WellCatalog,
) -> list[PdfPage]:
    reader = PdfReader(str(pdf_path))
    pages: list[PdfPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if not text:
            continue
        if not text.startswith("## "):
            text = f"## Body\n{text}"
        pages.append(
            _page_record(
                doc_id=doc_id,
                title=title,
                page=index,
                text=text,
                source_path=str(pdf_path),
                file_wells=file_wells,
                catalog=catalog,
            )
        )
    return pages


def _page_record(
    *,
    doc_id: str,
    title: str,
    page: int,
    text: str,
    source_path: str,
    file_wells: list[str],
    catalog: WellCatalog,
) -> PdfPage:
    well_ids = catalog.find_in_text(Path(source_path).name, text)
    if not well_ids and file_wells:
        well_ids = file_wells
    return PdfPage(
        doc_id=doc_id,
        title=title,
        page=page,
        text=text,
        source_path=source_path,
        well_ids=well_ids,
    )


def _layout_blocks_from_page(page: Any) -> list[LayoutBlock]:
    tables = list(page.find_tables() or [])
    table_bboxes = [table.bbox for table in tables]
    blocks: list[LayoutBlock] = []

    for table in tables:
        markdown = table_to_markdown(table.extract())
        if markdown:
            blocks.append(LayoutBlock(top=float(table.bbox[1]), kind="table", text=markdown))

    words = page.extract_words(extra_attrs=["size"]) or []
    outside = [
        word
        for word in words
        if not any(_word_in_bbox(word, bbox) for bbox in table_bboxes)
    ]
    for top, line_words in _cluster_words_into_lines(outside):
        text = " ".join(str(word.get("text") or "") for word in line_words).strip()
        if not text:
            continue
        sizes = [float(word.get("size") or 0) for word in line_words]
        font_size = max(sizes) if sizes else 0.0
        blocks.append(LayoutBlock(top=top, kind="line", text=text, font_size=font_size))
    return blocks


def _cluster_words_into_lines(
    words: list[dict[str, Any]],
) -> list[tuple[float, list[dict[str, Any]]]]:
    if not words:
        return []
    ordered = sorted(words, key=lambda word: (float(word["top"]), float(word["x0"])))
    lines: list[tuple[float, list[dict[str, Any]]]] = []
    current_top = float(ordered[0]["top"])
    current: list[dict[str, Any]] = []
    for word in ordered:
        top = float(word["top"])
        if current and abs(top - current_top) > _LINE_Y_TOLERANCE:
            current.sort(key=lambda item: float(item["x0"]))
            lines.append((current_top, current))
            current = [word]
            current_top = top
        else:
            current.append(word)
            current_top = min(current_top, top)
    if current:
        current.sort(key=lambda item: float(item["x0"]))
        lines.append((current_top, current))
    return lines


def _word_in_bbox(word: dict[str, Any], bbox: tuple[float, float, float, float]) -> bool:
    x0, top, x1, bottom = bbox
    cx = (float(word["x0"]) + float(word["x1"])) / 2
    cy = (float(word["top"]) + float(word["bottom"])) / 2
    return (x0 - _TABLE_PAD) <= cx <= (x1 + _TABLE_PAD) and (top - _TABLE_PAD) <= cy <= (
        bottom + _TABLE_PAD
    )


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
