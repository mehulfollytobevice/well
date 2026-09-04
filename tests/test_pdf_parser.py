"""Tests for well catalog and PDF text extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.sectioned_pdf import write_sectioned_fixture_pdf
from wellground.retrieval.pdf_parser import (
    LayoutBlock,
    PdfPage,
    guess_well_ids,
    is_generic_heading,
    make_doc_id,
    match_known_heading,
    parse_pdf,
    parse_pdf_corpus,
    render_layout_blocks,
    table_to_markdown,
    write_pages_jsonl,
)
from wellground.retrieval.well_catalog import WellCatalog, WellRecord

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WELLS_CSV = PROJECT_ROOT / "data/seed/wells.csv"
SAMPLE_PDF = (
    PROJECT_ROOT
    / "data/raw/pdfs/inj_prod/16A"
    / "University of Utah_Forge16A(78)-32_SLB_17Aug2024_Injection Profile Final Report.pdf"
)

FERVO_WELLS = (
    WellRecord("GOLD-4-PB", "Gold 4-PB"),
    WellRecord("GOLD-6-IB", "Gold 6-IB"),
    WellRecord("34A-22", "34A-22"),
    WellRecord("DELANO-1-OB", "Delano 1-OB"),
    WellRecord("73-22", "73-22"),
)


def test_guess_well_ids_from_utah_forge_catalog() -> None:
    catalog = WellCatalog.from_csv(WELLS_CSV)
    assert guess_well_ids("FORGE 16A(78)-32 Circulation Test RPT1.pdf", catalog=catalog) == ["16A"]
    assert guess_well_ids("FORGE 16B(78)-32 Circulation Test RPT2.pdf", catalog=catalog) == ["16B"]


def test_guess_well_ids_from_fervo_style_catalog() -> None:
    catalog = WellCatalog.from_records(FERVO_WELLS)

    assert catalog.find_in_text("Gold 4-PB mud log summary") == ["GOLD-4-PB"]
    assert catalog.find_in_text("Injection well 34A-22 cement evaluation") == ["34A-22"]
    assert catalog.find_in_text("Delano 1-OB DAS microseismic catalog") == ["DELANO-1-OB"]
    assert catalog.find_in_text("Gold 4-PB and Gold 6-IB stimulation") == ["GOLD-4-PB", "GOLD-6-IB"]


def test_duplicate_display_names_use_well_id_patterns() -> None:
    catalog = WellCatalog.from_records(
        (
            WellRecord("58-32", "58-32"),
            WellRecord("58-32-WW", "58-32"),
        )
    )

    assert catalog.find_in_text("Pilot well 58-32 stimulation") == ["58-32"]
    assert catalog.find_in_text("Water supply 58-32-WW inspection") == ["58-32-WW"]


def test_make_doc_id() -> None:
    pdf_path = Path("data/raw/pdfs/daily_reports/extracted/report.pdf")
    corpus_root = Path("data/raw/pdfs")
    assert make_doc_id(pdf_path, corpus_root) == "daily_reports/extracted/report"


def test_write_pages_jsonl(tmp_path: Path) -> None:
    pages = [
        PdfPage(
            doc_id="daily_reports/report",
            title="report",
            page=1,
            text="## Body\nSample text",
            source_path="/tmp/report.pdf",
            well_ids=["16A"],
        )
    ]
    output = tmp_path / "pages.jsonl"
    write_pages_jsonl(pages, output)

    saved = json.loads(output.read_text(encoding="utf-8").strip())
    assert saved["text"] == "## Body\nSample text"
    assert saved["well_ids"] == ["16A"]


def test_table_to_markdown() -> None:
    markdown = table_to_markdown(
        [
            ["From", "Description"],
            ["6:00", "RIGU"],
        ]
    )
    assert markdown.splitlines() == [
        "| From | Description |",
        "| --- | --- |",
        "| 6:00 | RIGU |",
    ]


def test_table_to_markdown_skips_empty_and_single_cell() -> None:
    assert table_to_markdown([]) == ""
    assert table_to_markdown([[None, None]]) == ""
    assert table_to_markdown([["only"]]) == ""


def test_match_known_heading() -> None:
    assert match_known_heading("Current Operations") == "Current Operations"
    assert match_known_heading("Operations Summary From To Elapsed") == "Operations Summary"
    assert match_known_heading("random paragraph about pumping.") is None


def test_generic_heading_requires_size_or_all_caps() -> None:
    assert is_generic_heading("INTRODUCTION", font_size=11, median_size=11)
    assert not is_generic_heading("Well Name", font_size=11, median_size=11)
    assert is_generic_heading("Conclusions", font_size=16, median_size=11)


def test_render_layout_blocks_emits_headings_and_tables() -> None:
    blocks = [
        LayoutBlock(top=10, kind="line", text="Current Operations", font_size=16),
        LayoutBlock(top=30, kind="line", text="Continue pumping at 10 bpm.", font_size=11),
        LayoutBlock(
            top=50,
            kind="table",
            text="| From | Description |\n| --- | --- |\n| 6:00 | RIGU |",
        ),
        LayoutBlock(top=90, kind="line", text="Safety Summary", font_size=16),
        LayoutBlock(top=110, kind="line", text="No incidents.", font_size=11),
    ]
    rendered = render_layout_blocks(blocks)
    assert "## Current Operations" in rendered
    assert "## Safety Summary" in rendered
    assert "| 6:00 | RIGU |" in rendered
    assert "Continue pumping at 10 bpm." in rendered


def test_render_layout_blocks_wraps_body_when_no_headings() -> None:
    blocks = [
        LayoutBlock(top=10, kind="line", text="A narrative paragraph.", font_size=11),
    ]
    assert render_layout_blocks(blocks) == "## Body\nA narrative paragraph."


def test_parse_fixture_pdf_sections_and_table(tmp_path: Path) -> None:
    pdf_path = write_sectioned_fixture_pdf(tmp_path / "sectioned.pdf")
    catalog = WellCatalog.from_csv(WELLS_CSV)
    pages = parse_pdf(pdf_path, corpus_root=tmp_path, catalog=catalog)

    assert len(pages) == 1
    text = pages[0].text
    assert "\n" in text
    assert "## Current Operations" in text
    assert "## Safety Summary" in text
    assert "|" in text
    assert "10 bpm" in text or "RIGU" in text or "No incidents" in text


@pytest.mark.skipif(not SAMPLE_PDF.is_file(), reason="Sample PDF not downloaded locally")
def test_parse_pdf_on_forge_report() -> None:
    catalog = WellCatalog.from_csv(WELLS_CSV)
    corpus_root = PROJECT_ROOT / "data/raw/pdfs"
    pages = parse_pdf(SAMPLE_PDF, corpus_root=corpus_root, catalog=catalog)

    assert pages
    assert pages[0].page == 1
    assert pages[0].well_ids == ["16A"]
    assert len(pages[0].text) > 50
    assert "\n" in pages[0].text
    assert "## " in pages[0].text or "|" in pages[0].text


@pytest.mark.skipif(not SAMPLE_PDF.is_file(), reason="Sample PDF not downloaded locally")
def test_parse_pdf_corpus_on_inj_prod_folder() -> None:
    catalog = WellCatalog.from_csv(WELLS_CSV)
    corpus_root = PROJECT_ROOT / "data/raw/pdfs"
    inj_prod = PROJECT_ROOT / "data/raw/pdfs/inj_prod/16A"
    pages = parse_pdf_corpus(inj_prod, corpus_root=corpus_root, catalog=catalog)

    assert pages
    assert all(page.well_ids == ["16A"] for page in pages)
