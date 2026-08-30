"""LangGraph agent state."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from wellground.agent.schemas import (
    AgentResponse,
    Evidence,
    RagEvidence,
    RouteDecision,
    SqlEvidence,
)


class AgentState(TypedDict, total=False):
    question: str
    run_id: str
    route_decision: RouteDecision | None
    sql_evidence: Annotated[list[SqlEvidence], operator.add]
    rag_evidence: Annotated[list[RagEvidence], operator.add]
    evidence: list[Evidence]
    response: AgentResponse | None
    verifier_feedback: str | None
    retry_count: int
