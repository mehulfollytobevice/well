"""Tests for BM25 sparse retrieval."""

from __future__ import annotations

from pathlib import Path

from wellground.retrieval.bm25_index import BM25Index, SearchHit, tokenize
from wellground.retrieval.chunker import Chunk


def _chunk(
    *,
    chunk_id: str = "daily_reports/rpt10#p001#c00",
    doc_id: str = "daily_reports/rpt10",
    title: str = "FORGE 16A(78)-32 Circulation Test RPT10",
    page: int = 1,
    text: str = "Report No. 10 covers wellhead pressure during circulation.",
    well_ids: list[str] | None = None,
    section: str = "",
) -> Chunk:
    if well_ids is None:
        well_ids = ["16A"]
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        title=title,
        page=page,
        text=text,
        well_ids=well_ids,
        token_count=10,
        section=section,
    )


def test_tokenize_keeps_forge_identifiers() -> None:
    tokens = tokenize("16A(78)-32 STIM1 Report No. 10 8-15-2024")
    assert "16a(78)-32" in tokens
    assert "stim1" in tokens
    assert "10" in tokens
    assert "8-15-2024" in tokens


def test_search_ranks_exact_report_match_first() -> None:
    chunks = [
        _chunk(
            chunk_id="a#p001#c00",
            doc_id="a",
            title="General geothermal overview",
            text="Enhanced geothermal systems use deep wells.",
            well_ids=[],
        ),
        _chunk(
            chunk_id="b#p001#c00",
            doc_id="b",
            title="FORGE 16A(78)-32 Circulation Test RPT10",
            text="Report No. 10 documents circulation test operations on 8-15-2024.",
            well_ids=["16A"],
        ),
    ]
    index = BM25Index.build(chunks)
    hits = index.search("FORGE 16A(78)-32 Circulation Test RPT10", top_k=2)

    assert len(hits) == 2
    assert hits[0].chunk.doc_id == "b"
    assert hits[0].rank == 1
    assert hits[0].score >= hits[1].score


def test_search_uses_title_and_well_ids() -> None:
    chunks = [
        _chunk(
            chunk_id="a#p001#c00",
            doc_id="a",
            title="Unrelated stimulation memo",
            text="Flow rates were stable throughout the day.",
            well_ids=["16B"],
        ),
        _chunk(
            chunk_id="b#p001#c00",
            doc_id="b",
            title="Daily operations summary",
            text="No major incidents were recorded.",
            well_ids=["16A"],
        ),
    ]
    index = BM25Index.build(chunks)
    hits = index.search("16A", top_k=1)

    assert hits[0].chunk.doc_id == "b"


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    chunks = [_chunk(section="Operations Summary")]
    original = BM25Index.build(chunks)
    original.save(tmp_path)

    loaded = BM25Index.load(tmp_path)
    hits = loaded.search("Report No. 10 circulation", top_k=1)

    assert len(loaded.chunks) == 1
    assert loaded.chunks[0].section == "Operations Summary"
    assert hits
    assert isinstance(hits[0], SearchHit)
    assert hits[0].chunk.chunk_id == chunks[0].chunk_id
