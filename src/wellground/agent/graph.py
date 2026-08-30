"""LangGraph: router → SQL/RAG workers → synthesizer → verifier."""

from __future__ import annotations

import time
import uuid
from functools import lru_cache
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from wellground.agent.nodes.rag_worker import rag_worker_node
from wellground.agent.nodes.router import router_node
from wellground.agent.nodes.sql_worker import sql_worker_node
from wellground.agent.nodes.synthesizer import synthesizer_node
from wellground.agent.nodes.verifier import verify_response
from wellground.agent.schemas import AgentResponse, RagEvidence, RouteDecision, SqlEvidence
from wellground.agent.state import AgentState
from wellground.observability.run_log import log_run
from wellground.tools.action import flag_well_for_review

MAX_VERIFY_RETRIES = 1


def merge_evidence_node(state: AgentState) -> dict[str, Any]:
    merged: list[SqlEvidence | RagEvidence] = []
    index = 1
    for item in state.get("sql_evidence") or []:
        merged.append(item.model_copy(update={"evidence_id": f"E{index}"}))
        index += 1
    seen_chunks: set[str] = set()
    for item in state.get("rag_evidence") or []:
        if item.chunk_id in seen_chunks:
            continue
        seen_chunks.add(item.chunk_id)
        merged.append(item.model_copy(update={"evidence_id": f"E{index}"}))
        index += 1
    return {"evidence": merged}


def verifier_node(state: AgentState) -> dict[str, Any]:
    response = state.get("response")
    if response is None:
        return {
            "response": AgentResponse(
                status="refused",
                route="unknown",
                claims=[],
                evidence=[],
                refusal_reason="Synthesizer did not return a response.",
            )
        }
    evidence = list(state.get("evidence") or [])
    ok, notes = verify_response(response, evidence)
    if ok:
        updated = response.model_copy(update={"verifier_notes": notes or None})
        return {"response": updated, "verifier_feedback": None}

    retry_count = state.get("retry_count") or 0
    if retry_count < MAX_VERIFY_RETRIES:
        return {"verifier_feedback": notes, "retry_count": retry_count + 1}

    route = state["route_decision"].route if state.get("route_decision") else "unknown"
    refused = AgentResponse(
        status="refused",
        route=route,
        claims=[],
        evidence=evidence,
        refusal_reason=notes,
        verifier_notes=notes,
    )
    return {"response": refused, "verifier_feedback": None}


def action_stub_node(state: AgentState) -> dict[str, Any]:
    flag_well_for_review(well_id="", reason=state["question"])
    return {
        "response": AgentResponse(
            status="refused",
            route="action",
            claims=[],
            evidence=[],
            refusal_reason="HITL actions are not implemented yet.",
        )
    }


def dispatch_workers(
    state: AgentState,
) -> list[Send] | Literal["action_stub"]:
    decision: RouteDecision | None = state.get("route_decision")
    route = decision.route if decision else "rag"
    if route == "action":
        return "action_stub"
    sends: list[Send] = []
    if route in {"sql", "both"}:
        sends.append(Send("sql_worker", state))
    if route in {"rag", "both"}:
        sends.append(Send("rag_worker", state))
    return sends


def after_verifier(state: AgentState) -> Literal["retry", "done"]:
    if state.get("verifier_feedback"):
        return "retry"
    return "done"


def build_graph() -> StateGraph[AgentState]:
    graph: StateGraph[AgentState] = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("sql_worker", sql_worker_node)
    graph.add_node("rag_worker", rag_worker_node)
    graph.add_node("action_stub", action_stub_node)
    graph.add_node("merge_evidence", merge_evidence_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("verifier", verifier_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        dispatch_workers,
        ["sql_worker", "rag_worker", "action_stub"],
    )
    graph.add_edge("sql_worker", "merge_evidence")
    graph.add_edge("rag_worker", "merge_evidence")
    graph.add_edge("action_stub", END)
    graph.add_edge("merge_evidence", "synthesizer")
    graph.add_edge("synthesizer", "verifier")
    graph.add_conditional_edges(
        "verifier",
        after_verifier,
        {"retry": "synthesizer", "done": END},
    )
    return graph


@lru_cache
def get_compiled_graph() -> CompiledStateGraph:
    return build_graph().compile()


def run_agent(question: str) -> AgentResponse:
    started = time.perf_counter()
    run_id = str(uuid.uuid4())
    result = get_compiled_graph().invoke(
        {
            "question": question,
            "run_id": run_id,
            "sql_evidence": [],
            "rag_evidence": [],
            "evidence": [],
            "retry_count": 0,
            "verifier_feedback": None,
            "response": None,
            "route_decision": None,
        }
    )
    response: AgentResponse = result["response"]
    log_run(
        run_id=run_id,
        question=question,
        route=response.route,
        status=response.status,
        evidence_count=len(response.evidence),
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return response
