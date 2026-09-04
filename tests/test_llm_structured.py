"""Structured-output payload unwrapping (no live LLM)."""

from __future__ import annotations

from wellground.agent.llm import _normalize_structured_payload
from wellground.agent.schemas import RouteDecision, SqlPlan, SynthesisResult


def test_unwraps_name_value_schema_echo() -> None:
    payload = {
        "name": "route",
        "value": "sql",
        "rationale": "catalog lookup",
        "rag_subquery": None,
    }
    out = _normalize_structured_payload(payload, RouteDecision)
    assert out["route"] == "sql"
    RouteDecision.model_validate(out)


def test_unwraps_titled_wrapper() -> None:
    payload = {
        "RouteDecision": {
            "route": "rag",
            "rationale": "daily report",
            "sql_subquery": None,
            "rag_subquery": "EV camera",
        }
    }
    out = _normalize_structured_payload(payload, RouteDecision)
    assert out["route"] == "rag"
    RouteDecision.model_validate(out)


def test_parses_stringified_params_object() -> None:
    payload = {
        "mode": "metric",
        "metric_id": "well_role",
        "params": '{"well_id":"16B"}',
        "sql": None,
    }
    out = _normalize_structured_payload(payload, SqlPlan)
    assert out["params"] == {"well_id": "16B"}
    SqlPlan.model_validate(out)


def test_synthesis_accepts_claim_instead_of_text() -> None:
    payload = {
        "status": "answered",
        "claims": [
            {
                "claim": "Step 7 of the 16A circulation test was pumped at 10.0 bpm.",
                "source_ids": ["E4", "E6"],
            }
        ],
        "refusal_reason": None,
    }
    result = SynthesisResult.model_validate(payload)
    assert result.claims[0].text.startswith("Step 7")
