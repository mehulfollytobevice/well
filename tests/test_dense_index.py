"""Tests for dense-index chunk metadata (no Chroma I/O)."""

from __future__ import annotations

from wellground.retrieval.chunker import Chunk
from wellground.retrieval.dense_index import _chunk_from_metadata, _chunk_metadata


def test_chunk_metadata_round_trip_includes_section() -> None:
    chunk = Chunk(
        chunk_id="daily_reports/rpt#p001#c00",
        doc_id="daily_reports/rpt",
        title="RPT10",
        page=1,
        text="## Operations Summary\n| From | To |\n| --- | --- |\n| 6:00 | 7:00 |",
        well_ids=["16A", "16B"],
        token_count=20,
        section="Operations Summary",
    )
    metadata = _chunk_metadata(chunk)
    assert metadata["section"] == "Operations Summary"
    assert metadata["well_ids"] == "16A,16B"

    restored = _chunk_from_metadata(chunk.chunk_id, metadata)
    assert restored.section == "Operations Summary"
    assert restored.well_ids == ["16A", "16B"]
    assert restored.text == chunk.text


def test_chunk_from_metadata_defaults_missing_section() -> None:
    restored = _chunk_from_metadata(
        "id#p001#c00",
        {
            "doc_id": "doc",
            "title": "Title",
            "page": 1,
            "text": "plain",
            "well_ids": "16A",
            "token_count": 4,
        },
    )
    assert restored.section == ""
    assert restored.well_ids == ["16A"]
