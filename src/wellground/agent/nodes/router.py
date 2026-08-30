"""Router node: classify intent into sql | rag | both | action."""

from __future__ import annotations

from typing import Any

from wellground.agent import llm as llm
from wellground.agent.schemas import RouteDecision
from wellground.agent.state import AgentState

ROUTER_PROMPT = """You route questions about the Utah FORGE geothermal site.

Pick exactly one route:
- sql: well metadata or numeric time-series (flow, pressure, temperature)
- rag: reports, procedures, stimulation, daily ops, qualitative history
- both: needs numbers AND report/document context
- action: user wants to flag a well or take an operational action

For sql or both, set sql_subquery to a short search/query rewrite.
For rag or both, set rag_subquery to a short retrieval query.
Otherwise leave those fields null.

Question: {question}
"""


def router_node(state: AgentState) -> dict[str, Any]:
    decision = llm.complete_structured(
        ROUTER_PROMPT.format(question=state["question"]),
        RouteDecision,
    )
    if decision.route in {"sql", "both"} and not decision.sql_subquery:
        decision = decision.model_copy(update={"sql_subquery": state["question"]})
    if decision.route in {"rag", "both"} and not decision.rag_subquery:
        decision = decision.model_copy(update={"rag_subquery": state["question"]})
    return {"route_decision": decision}
