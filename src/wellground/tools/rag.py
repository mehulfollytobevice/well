"""RAG tool wrapping HybridRetriever as citation-ready evidence."""

from __future__ import annotations

import re

from wellground.agent.schemas import RagEvidence
from wellground.config import get_settings
from wellground.retrieval.hybrid import HybridHit, HybridRetriever

EXCERPT_CHARS = 500

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        settings = get_settings()
        _retriever = HybridRetriever.load(
            bm25_dir=settings.wellground_bm25_path,
            chroma_dir=settings.wellground_chroma_path,
        )
    return _retriever


def search_docs(
    query: str,
    *,
    top_k: int = 6,
    retriever: HybridRetriever | None = None,
) -> list[RagEvidence]:
    hits = (retriever or get_retriever()).search(query, top_k=top_k)
    return [hit_to_evidence(hit) for hit in hits]


def hit_to_evidence(hit: HybridHit) -> RagEvidence:
    chunk = hit.chunk
    return RagEvidence(
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        title=chunk.title,
        page=chunk.page,
        excerpt=_excerpt(chunk.text),
        well_ids=list(chunk.well_ids),
        score=hit.score,
        section=chunk.section,
    )


def _excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    """Truncate for the LLM while keeping markdown table line breaks."""
    collapsed = re.sub(r"[ \t]+", " ", text)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."
