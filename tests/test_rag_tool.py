"""Tests for HybridHit → RagEvidence mapping."""

from __future__ import annotations

from wellground.retrieval.chunker import Chunk
from wellground.retrieval.hybrid import HybridHit
from wellground.tools.rag import hit_to_evidence


def test_hit_to_evidence_copies_citation_fields() -> None:
    chunk = Chunk(
        chunk_id="daily_reports/extracted/rpt#p003#c01",
        doc_id="daily_reports/extracted/rpt",
        title="Circulation Test RPT10",
        page=3,
        text="16A was hydraulically stimulated in April 2022.",
        well_ids=["16A"],
        token_count=12,
    )
    hit = HybridHit(
        chunk_id=chunk.chunk_id,
        chunk=chunk,
        score=0.032,
        rank=1,
        bm25_rank=1,
        dense_rank=2,
    )
    evidence = hit_to_evidence(hit)
    assert evidence.chunk_id == chunk.chunk_id
    assert evidence.doc_id == chunk.doc_id
    assert evidence.title == chunk.title
    assert evidence.page == 3
    assert "stimulated" in evidence.excerpt
    assert evidence.well_ids == ["16A"]
    assert evidence.score == 0.032
    assert evidence.evidence_id == ""
    assert evidence.section == ""


def test_hit_to_evidence_preserves_section_and_table_newlines() -> None:
    table = (
        "## Operations Summary\n"
        "| From | Description |\n"
        "| --- | --- |\n"
        "| 6:00 | RIGU |"
    )
    chunk = Chunk(
        chunk_id="daily_reports/extracted/rpt#p001#c00",
        doc_id="daily_reports/extracted/rpt",
        title="RPT10",
        page=1,
        text=table,
        well_ids=["16A"],
        token_count=30,
        section="Operations Summary",
    )
    hit = HybridHit(
        chunk_id=chunk.chunk_id,
        chunk=chunk,
        score=0.1,
        rank=1,
        bm25_rank=1,
        dense_rank=1,
    )
    evidence = hit_to_evidence(hit)
    assert evidence.section == "Operations Summary"
    assert "\n" in evidence.excerpt
    assert "| 6:00 | RIGU |" in evidence.excerpt
