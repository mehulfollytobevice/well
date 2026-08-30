"""Synthesizer: merge numbered evidence into cited claims."""

from __future__ import annotations

import json
from typing import Any

from wellground.agent import llm
from wellground.agent.schemas import (
    AgentResponse,
    Evidence,
    RagEvidence,
    SqlEvidence,
    SynthesisResult,
)
from wellground.agent.state import AgentState

SYNTH_PROMPT = """You answer a Utah FORGE question using ONLY the evidence below.
Each evidence item has an id like E1, E2.

Rules:
- Every factual claim MUST include source_ids drawn from those ids.
- Do not invent ids or facts that are not in the evidence.
- If evidence is too thin, set status to refused and explain in refusal_reason.
- status=answered requires one or more claims.

Question: {question}

Evidence:
{evidence_block}
{feedback}
"""


def synthesizer_node(state: AgentState) -> dict[str, Any]:
    evidence = state.get("evidence") or []
    route = state["route_decision"].route if state.get("route_decision") else "unknown"
    if not evidence:
        return {
            "response": AgentResponse(
                status="refused",
                route=route,
                claims=[],
                evidence=[],
                refusal_reason="No evidence retrieved.",
            )
        }

    feedback = state.get("verifier_feedback")
    feedback_block = ""
    if feedback:
        feedback_block = f"\nPrevious draft failed verification: {feedback}\nFix the claims.\n"
    result = llm.complete_structured(
        SYNTH_PROMPT.format(
            question=state["question"],
            evidence_block=_format_evidence(evidence),
            feedback=feedback_block,
        ),
        SynthesisResult,
    )
    return {
        "response": AgentResponse(
            status=result.status,
            route=route,
            claims=result.claims,
            evidence=evidence,
            refusal_reason=result.refusal_reason,
        )
    }


def _format_evidence(evidence: list[Evidence]) -> str:
    blocks: list[str] = []
    for item in evidence:
        if isinstance(item, SqlEvidence):
            rows = json.dumps(item.rows, default=str)
            blocks.append(
                f"[{item.evidence_id}] SQL metric={item.metric_id} source={item.source}\n"
                f"SQL: {item.sql}\nRows: {rows}"
            )
        elif isinstance(item, RagEvidence):
            wells = ",".join(item.well_ids) or "none"
            blocks.append(
                f"[{item.evidence_id}] RAG {item.title} p.{item.page} "
                f"chunk={item.chunk_id} wells={wells}\n{item.excerpt}"
            )
    return "\n\n".join(blocks)
