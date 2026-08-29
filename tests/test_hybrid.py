"""Tests for hybrid RRF retrieval."""

from __future__ import annotations

from wellground.retrieval.hybrid import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_prefers_chunks_in_both_lists() -> None:
    bm25_ranking = ["a", "b", "c"]
    dense_ranking = ["b", "d", "a"]

    fused = reciprocal_rank_fusion([bm25_ranking, dense_ranking], k=60)
    scores = dict(fused)

    assert scores["b"] > scores["a"]
    assert scores["a"] > scores["c"]
    assert scores["a"] > scores["d"]
    assert fused[0][0] == "b"


def test_reciprocal_rank_fusion_handles_single_source() -> None:
    fused = reciprocal_rank_fusion([["x", "y", "z"]], k=60)
    assert [chunk_id for chunk_id, _score in fused] == ["x", "y", "z"]
