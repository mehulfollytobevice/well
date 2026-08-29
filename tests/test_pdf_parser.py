"""Tests for well catalog and PDF text extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wellground.retrieval.pdf_parser import (
    PdfPage,
    guess_well_ids,
    make_doc_id,
    parse_pdf,
    parse_pdf_corpus,
    write_pages_jsonl,
)
from wellground.retrieval.well_catalog import WellCatalog, WellRecord

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WELLS_CSV = PROJECT_ROOT / "data/seed/wells.csv"
SAMPLE_PDF = (
    PROJECT_ROOT
    / "data/raw/pdfs/inj_prod/16A/University of Utah_Forge16A(78)-32_SLB_17Aug2024_Injection Profile Final Report.pdf"
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
            text="Sample text",
            source_path="/tmp/report.pdf",
            well_ids=["16A"],
        )
    ]
    output = tmp_path / "pages.jsonl"
    write_pages_jsonl(pages, output)

    saved = json.loads(output.read_text(encoding="utf-8").strip())
    assert saved["text"] == "Sample text"
    assert saved["well_ids"] == ["16A"]


@pytest.mark.skipif(not SAMPLE_PDF.is_file(), reason="Sample PDF not downloaded locally")
def test_parse_pdf_on_forge_report() -> None:
    catalog = WellCatalog.from_csv(WELLS_CSV)
    corpus_root = PROJECT_ROOT / "data/raw/pdfs"
    pages = parse_pdf(SAMPLE_PDF, corpus_root=corpus_root, catalog=catalog)

    assert pages
    assert pages[0].page == 1
    assert pages[0].well_ids == ["16A"]
    assert len(pages[0].text) > 50


@pytest.mark.skipif(not SAMPLE_PDF.is_file(), reason="Sample PDF not downloaded locally")
def test_parse_pdf_corpus_on_inj_prod_folder() -> None:
    catalog = WellCatalog.from_csv(WELLS_CSV)
    corpus_root = PROJECT_ROOT / "data/raw/pdfs"
    inj_prod = PROJECT_ROOT / "data/raw/pdfs/inj_prod/16A"
    pages = parse_pdf_corpus(inj_prod, corpus_root=corpus_root, catalog=catalog)

    assert pages
    assert all(page.well_ids == ["16A"] for page in pages)
