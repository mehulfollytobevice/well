"""BM25 sparse retrieval over chunked PDF passages."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from wellground.retrieval.chunker import Chunk

DEFAULT_INDEX_DIR = Path("data/processed/bm25")
CHUNKS_FILENAME = "chunks.jsonl"
INDEX_FILENAME = "index.pkl"

# Split on whitespace; strip edge punctuation but keep internal ids like 16a(78)-32.
_EDGE_PUNCT = ".,;:!?\"'[]{}"

@dataclass(frozen=True)
class SearchHit:
    """One BM25-ranked chunk with score and rank (1-based)."""

    chunk: Chunk
    score: float
    rank: int


def tokenize(text: str) -> list[str]:
    """Lowercase tokens suited to FORGE ids, dates, and acronyms."""
    tokens: list[str] = []
    for raw in text.lower().split():
        token = raw.strip(_EDGE_PUNCT)
        if token:
            tokens.append(token)
    return tokens


def chunk_index_text(chunk: Chunk) -> str:
    """Text passed to BM25 — title, section, and well tags help keyword lookup."""
    parts = [chunk.title]
    if chunk.section:
        parts.append(chunk.section)
    if chunk.well_ids:
        parts.append(" ".join(chunk.well_ids))
    parts.append(chunk.text)
    return "\n".join(parts)


def _token_overlap(query_tokens: list[str], doc_tokens: list[str]) -> int:
    """Count distinct query tokens present in a document (tiebreaker)."""
    doc_set = set(doc_tokens)
    return sum(1 for token in query_tokens if token in doc_set)


class BM25Index:
    """In-memory BM25 index over a fixed chunk corpus."""

    def __init__(self, chunks: list[Chunk]) -> None:
        if not chunks:
            raise ValueError("BM25Index requires at least one chunk")
        self.chunks = list(chunks)
        self._corpus_tokens = [tokenize(chunk_index_text(chunk)) for chunk in self.chunks]
        self._bm25 = BM25Okapi(self._corpus_tokens)

    def search(self, query: str, *, top_k: int = 6) -> list[SearchHit]:
        """Return the top-k chunks ranked by BM25 score."""
        if top_k <= 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda idx: (
                scores[idx],
                _token_overlap(query_tokens, self._corpus_tokens[idx]),
            ),
            reverse=True,
        )

        hits: list[SearchHit] = []
        for rank, idx in enumerate(ranked_indices[:top_k], start=1):
            hits.append(
                SearchHit(chunk=self.chunks[idx], score=float(scores[idx]), rank=rank)
            )
        return hits

    def save(self, directory: Path) -> None:
        """Persist chunks and the BM25 model under ``directory``."""
        directory.mkdir(parents=True, exist_ok=True)

        chunks_path = directory / CHUNKS_FILENAME
        with chunks_path.open("w", encoding="utf-8") as handle:
            for chunk in self.chunks:
                handle.write(
                    json.dumps(
                        {
                            "chunk_id": chunk.chunk_id,
                            "doc_id": chunk.doc_id,
                            "title": chunk.title,
                            "page": chunk.page,
                            "text": chunk.text,
                            "well_ids": chunk.well_ids,
                            "token_count": chunk.token_count,
                            "section": chunk.section,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        index_path = directory / INDEX_FILENAME
        payload = {
            "version": 1,
            "corpus_tokens": self._corpus_tokens,
            "bm25": self._bm25,
        }
        with index_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, directory: Path) -> BM25Index:
        """Load a saved index from ``directory``."""
        chunks_path = directory / CHUNKS_FILENAME
        index_path = directory / INDEX_FILENAME
        if not chunks_path.is_file() or not index_path.is_file():
            raise FileNotFoundError(
                f"BM25 index not found in {directory}. "
                f"Expected {CHUNKS_FILENAME} and {INDEX_FILENAME}."
            )

        chunks: list[Chunk] = []
        with chunks_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                chunks.append(Chunk.from_mapping(row))

        with index_path.open("rb") as handle:
            payload = pickle.load(handle)

        index = cls.__new__(cls)
        index.chunks = chunks
        index._corpus_tokens = payload["corpus_tokens"]
        index._bm25 = payload["bm25"]
        return index

    @classmethod
    def build(cls, chunks: list[Chunk]) -> BM25Index:
        """Create a BM25 index from an in-memory chunk list."""
        return cls(chunks)
