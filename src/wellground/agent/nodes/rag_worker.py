"""RAG worker: retrieve report chunks as evidence."""

from __future__ import annotations

from typing import Any

from wellground.agent.state import AgentState
from wellground.tools import rag as rag_tools


def rag_worker_node(state: AgentState) -> dict[str, Any]:
    decision = state["route_decision"]
    query = (decision.rag_subquery if decision else None) or state["question"]
    return {"rag_evidence": rag_tools.search_docs(query)}
