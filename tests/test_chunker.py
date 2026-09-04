"""Tests for PDF page chunking."""

from __future__ import annotations

import json
from pathlib import Path

import tiktoken

from wellground.retrieval.chunker import (
    Chunk,
    chunk_page,
    chunk_pages,
    count_tokens,
    load_pages_jsonl,
    make_chunk_id,
    split_sections,
    write_chunks_jsonl,
)
from wellground.retrieval.pdf_parser import PdfPage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGES_JSONL = PROJECT_ROOT / "data/processed/pdf_pages.jsonl"


def test_make_chunk_id() -> None:
    assert make_chunk_id("daily_reports/report", 1, 0) == "daily_reports/report#p001#c00"
    assert make_chunk_id("daily_reports/report", 12, 3) == "daily_reports/report#p012#c03"


def test_chunk_from_mapping_defaults_missing_section() -> None:
    chunk = Chunk.from_mapping(
        {
            "chunk_id": "doc#p001#c00",
            "doc_id": "doc",
            "title": "Title",
            "page": 1,
            "text": "plain",
            "well_ids": ["16A"],
            "token_count": 4,
        }
    )
    assert chunk.section == ""
    assert chunk.well_ids == ["16A"]


def test_split_sections_reads_markdown_headings() -> None:
    sections = split_sections(
        "## Current Operations\nPumping.\n\n## Safety Summary\nNo incidents."
    )
    assert [name for name, _body in sections] == ["Current Operations", "Safety Summary"]


def test_short_page_becomes_single_chunk() -> None:
    page = PdfPage(
        doc_id="test/doc",
        title="Test",
        page=1,
        text="Short passage about well 16A pressure.",
        source_path="/tmp/test.pdf",
        well_ids=["16A"],
    )
    chunks = chunk_page(page, max_tokens=600)

    assert len(chunks) == 1
    assert chunks[0].well_ids == ["16A"]
    assert chunks[0].section == "Body"
    assert chunks[0].text.startswith("## Body")
    assert chunks[0].token_count == count_tokens(chunks[0].text)
    assert chunks[0].chunk_id == "test/doc#p001#c00"


def test_two_sections_become_two_chunks() -> None:
    page = PdfPage(
        doc_id="test/doc",
        title="Test",
        page=1,
        text="## Current Operations\nPumping at 10 bpm.\n\n## Safety Summary\nNo incidents.",
        source_path="/tmp/test.pdf",
        well_ids=["16A"],
    )
    chunks = chunk_page(page, max_tokens=600)

    assert len(chunks) == 2
    assert [chunk.section for chunk in chunks] == ["Current Operations", "Safety Summary"]
    assert chunks[0].text.startswith("## Current Operations")
    assert "10 bpm" in chunks[0].text
    assert "No incidents" in chunks[1].text
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_long_section_splits_with_overlap() -> None:
    enc = tiktoken.get_encoding("cl100k_base")
    long_text = enc.decode(list(range(2000)))
    page = PdfPage(
        doc_id="test/doc",
        title="Test",
        page=2,
        text=f"## Operations Summary\n{long_text}",
        source_path="/tmp/test.pdf",
        well_ids=[],
    )

    chunks = chunk_page(page, max_tokens=600, overlap_tokens=100)

    assert len(chunks) >= 3
    assert all(chunk.token_count <= 600 for chunk in chunks)
    assert all(chunk.section == "Operations Summary" for chunk in chunks)
    assert all(chunk.text.startswith("## Operations Summary") for chunk in chunks)
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_empty_page_returns_no_chunks() -> None:
    page = PdfPage(
        doc_id="test/doc",
        title="Test",
        page=1,
        text="",
        source_path="/tmp/test.pdf",
        well_ids=[],
    )
    assert chunk_page(page) == []


def test_write_and_load_chunks_jsonl(tmp_path: Path) -> None:
    page = PdfPage(
        doc_id="test/doc",
        title="Test",
        page=1,
        text="## Body\nSample chunk text.",
        source_path="/tmp/test.pdf",
        well_ids=["16B"],
    )
    chunks = chunk_page(page)
    output = tmp_path / "chunks.jsonl"
    write_chunks_jsonl(chunks, output)

    saved = json.loads(output.read_text(encoding="utf-8").strip())
    assert "Sample chunk text." in saved["text"]
    assert saved["well_ids"] == ["16B"]
    assert saved["section"] == "Body"


def test_chunk_pages_round_trip(tmp_path: Path) -> None:
    pages = [
        PdfPage(
            doc_id="test/a",
            title="A",
            page=1,
            text="First page.",
            source_path="/tmp/a.pdf",
            well_ids=["16A"],
        ),
        PdfPage(
            doc_id="test/b",
            title="B",
            page=1,
            text="Second page.",
            source_path="/tmp/b.pdf",
            well_ids=["16B"],
        ),
    ]
    pages_path = tmp_path / "pages.jsonl"
    with pages_path.open("w", encoding="utf-8") as handle:
        for page in pages:
            handle.write(json.dumps(page.__dict__, ensure_ascii=False) + "\n")

    loaded = load_pages_jsonl(pages_path)
    chunks = chunk_pages(loaded)

    assert len(chunks) == 2
    assert {chunk.doc_id for chunk in chunks} == {"test/a", "test/b"}


def test_chunk_real_corpus_if_available() -> None:
    if not PAGES_JSONL.is_file():
        return

    pages = load_pages_jsonl(PAGES_JSONL)
    chunks = chunk_pages(pages)

    assert len(chunks) >= len(pages)
    assert all(chunk.token_count <= 600 for chunk in chunks)
    assert all(chunk.text for chunk in chunks)
