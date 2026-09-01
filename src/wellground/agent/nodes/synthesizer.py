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

SYNTH_SYSTEM_PROMPT = """You synthesize answers for Utah FORGE geothermal operations staff using ONLY retrieved evidence.

Your output is structured JSON (claims + status). Write claim text for an operator: clear, direct, and actionable.

Evidence ids (E1, E2, ...) must appear in every claim's source_ids.

Decision rules:
1. status=answered — evidence supports one or more factual claims.
2. status=needs_clarification — evidence is related but insufficient or ambiguous; explain what is missing in refusal_reason.
3. status=refused — evidence is empty, irrelevant, or too thin to say anything useful.

Claim rules (when status=answered):
- One atomic fact or insight per claim; use multiple claims to build a fuller answer.
- Every claim MUST cite source_ids from the evidence list only.
- Claim text MUST reuse specific terms, numbers, well ids, units, or dates from cited evidence (required for verification).
- Do not invent facts, ids, or sources.

Adapt your answer style to the question type:

1. Factual claims and numbers (what / when / how much):
   - Give a straightforward, direct answer.
   - Lead with the key value or fact; cite the supporting evidence.
   - Example tone: "Well 16A injection rate was 42 gpm on 2022-04-15."

2. Trends and analysis (how changed over time, compare wells, patterns):
   - Write a short coherent analysis across claims.
   - Order claims logically: context → trend → implication.
   - Describe direction, magnitude, and time window when evidence supports it.
   - Each analytical point must still cite its own source_ids.

3. Well functioning and status (is X operating normally, current state):
   - Write in status-report style: overall condition first, then supporting details.
   - Cover relevant metrics (flow, pressure, temperature) and operational notes from evidence.
   - Flag uncertainty or missing data explicitly in a claim or refusal_reason.

4. Anomalies and peaks (spikes, drops, unusual events):
   - Focus on numeric evidence: identify spikes, step changes, or outliers.
   - State the metric, well, timestamp or period, and approximate magnitude of change.
   - Contrast anomalous values against nearby normal readings when evidence allows.
   - If evidence lacks time-series detail, refuse or ask for clarification rather than speculating.

When a previous draft failed verification, fix the specific issues noted."""

SYNTH_USER_PROMPT = """Question: {question}

Evidence:
{evidence_block}
{feedback}"""


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
        SYNTH_USER_PROMPT.format(
            question=state["question"],
            evidence_block=_format_evidence(evidence),
            feedback=feedback_block,
        ),
        SynthesisResult,
        system=SYNTH_SYSTEM_PROMPT,
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
