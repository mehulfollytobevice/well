"""Hybrid retrieval: BM25 + dense with reciprocal rank fusion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wellground.retrieval.bm25_index import BM25Index
from wellground.retrieval.chunker import Chunk
from wellground.retrieval.dense_index import DEFAULT_CHROMA_DIR, DenseIndex

DEFAULT_BM25_DIR = Path("data/processed/bm25")
DEFAULT_RRF_K = 60


@dataclass(frozen=True)
class HybridHit:
    """One fused retrieval result with per-source ranks."""

    chunk_id: str
    chunk: Chunk
    score: float  # cosine similarity in [~-1, 1], used as UI relevance
    rank: int
    bm25_rank: int | None
    dense_rank: int | None


def reciprocal_rank_fusion(
    ranked_ids: list[list[str]],
    *,
    k: int = DEFAULT_RRF_K,
) -> list[tuple[str, float]]:
    """Merge ranked chunk-id lists with standard RRF scoring."""
    scores: dict[str, float] = {}
    for ranking in ranked_ids:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


class HybridRetriever:
    """Run BM25 and dense search, then fuse with RRF."""

    def __init__(
        self,
        bm25: BM25Index,
        dense: DenseIndex,
        *,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.rrf_k = rrf_k
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in bm25.chunks}

    @classmethod
    def load(
        cls,
        *,
        bm25_dir: Path = DEFAULT_BM25_DIR,
        chroma_dir: Path = DEFAULT_CHROMA_DIR,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> HybridRetriever:
        return cls(BM25Index.load(bm25_dir), DenseIndex.load(chroma_dir), rrf_k=rrf_k)

    def search(self, query: str, *, top_k: int = 6) -> list[HybridHit]:
        """Return fused top-k chunks."""
        bm25_hits = self.bm25.search(query, top_k=top_k)
        dense_hits = self.dense.search(query, top_k=top_k)

        bm25_ranks = {hit.chunk.chunk_id: hit.rank for hit in bm25_hits}
        dense_ranks = {hit.chunk.chunk_id: hit.rank for hit in dense_hits}
        chunk_by_id = {
            hit.chunk.chunk_id: hit.chunk for hit in bm25_hits + dense_hits
        }

        fused = reciprocal_rank_fusion(
            [
                [hit.chunk.chunk_id for hit in bm25_hits],
                [hit.chunk.chunk_id for hit in dense_hits],
            ],
            k=self.rrf_k,
        )

        dense_scores = {hit.chunk.chunk_id: hit.score for hit in dense_hits}
        fused_ids = [chunk_id for chunk_id, _rrf in fused[:top_k]]
        cosine_by_id = self.dense.cosine_scores(query, fused_ids)

        hits: list[HybridHit] = []
        for rank, (chunk_id, _rrf_score) in enumerate(fused[:top_k], start=1):
            chunk = chunk_by_id.get(chunk_id) or self._chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            hits.append(
                HybridHit(
                    chunk_id=chunk_id,
                    chunk=chunk,
                    score=cosine_by_id.get(chunk_id, dense_scores.get(chunk_id, 0.0)),
                    rank=rank,
                    bm25_rank=bm25_ranks.get(chunk_id),
                    dense_rank=dense_ranks.get(chunk_id),
                )
            )
        return hits
