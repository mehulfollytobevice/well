"""Layer A: hybrid retrieval Hit@k on release indexes (doc_id + page)."""

from __future__ import annotations

import pytest

from wellground.evals.graders import grade_retrieval
from wellground.evals.loader import cases_for_tag
from wellground.evals.schema import GoldCase
from wellground.retrieval.hybrid import HybridRetriever
from wellground.tools.rag import search_docs

_CASES = cases_for_tag("rag")
_TOP_K = 6


@pytest.mark.parametrize("gold", _CASES, ids=lambda c: c.id)
def test_rag_retrieval(gold: GoldCase, release_retriever: HybridRetriever) -> None:
    hits = search_docs(gold.retrieval_query(), top_k=_TOP_K, retriever=release_retriever)
    result = grade_retrieval(hits, gold, top_k=_TOP_K)
    assert result.passed, result.message
