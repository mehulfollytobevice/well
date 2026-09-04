"""Router node: classify intent into sql | rag | both | action."""

from __future__ import annotations

from typing import Any

from wellground.agent import llm as llm
from wellground.agent.schemas import RouteDecision
from wellground.agent.state import AgentState

ROUTER_PROMPT = """You route questions about the Utah FORGE geothermal site.

Pick exactly one route:
- sql: well catalog metadata or numeric time-series (flow, pressure, temperature)
- rag: reports, procedures, stimulation steps, daily ops, qualitative history
- both: the question itself asks for a catalog/timeseries number AND a document/report citation
- action: user wants to flag a well or take an operational action

Hard rules:
- Catalog attributes (role, well count, list wells, GPS) are sql, never rag.
- Averages/peaks of flow, pressure, or temperature during the circulation test are sql.
  Mentioning a "test" does not mean both — those numbers live in DuckDB timeseries.
- Daily-report facts (Step N pump rate, EV camera, rig activity, procedures) are rag.
  Pump rate by stimulation step is not in timeseries tables, so do not pick sql or both.
- both only if the user asks for a number from the catalog/timeseries AND to cite a report.

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
