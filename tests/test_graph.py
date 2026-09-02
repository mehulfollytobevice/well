"""Graph tests with a mocked LLM (no Fireworks calls)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from wellground.agent.graph import build_graph
from wellground.agent.schemas import (
    Claim,
    RagEvidence,
    RouteDecision,
    SqlEvidence,
    SqlPlan,
    SynthesisResult,
)


def _rag_hit() -> RagEvidence:
    return RagEvidence(
        chunk_id="daily_reports/extracted/rpt#p001#c00",
        doc_id="daily_reports/extracted/rpt",
        title="RPT10",
        page=1,
        excerpt="16A was hydraulically stimulated in April 2022.",
        well_ids=["16A"],
        score=0.05,
    )


def test_rag_route_cites_evidence_ids(monkeypatch: Any) -> None:
    def fake_complete(prompt: str, schema: type[BaseModel], **_kwargs: Any) -> BaseModel:
        if schema is RouteDecision:
            return RouteDecision(
                route="rag",
                rationale="question is about reports",
                rag_subquery="16A stimulation",
            )
        if schema is SynthesisResult:
            return SynthesisResult(
                status="answered",
                claims=[
                    Claim(
                        text="16A was hydraulically stimulated in April 2022.",
                        source_ids=["E1"],
                    )
                ],
            )
        raise AssertionError(f"unexpected schema {schema}")

    monkeypatch.setattr("wellground.agent.llm.complete_structured", fake_complete)
    monkeypatch.setattr("wellground.tools.rag.search_docs", lambda query, **kwargs: [_rag_hit()])

    result = build_graph().compile().invoke(
        {
            "question": "How was 16A stimulated?",
            "run_id": "test",
            "sql_evidence": [],
            "rag_evidence": [],
            "evidence": [],
            "retry_count": 0,
            "verifier_feedback": None,
        }
    )
    response = result["response"]
    assert response.status == "answered"
    assert response.route == "rag"
    assert response.claims[0].source_ids == ["E1"]
    assert response.evidence[0].evidence_id == "E1"
    assert response.evidence[0].chunk_id == _rag_hit().chunk_id


def test_action_route_refuses(monkeypatch: Any) -> None:
    def fake_complete(prompt: str, schema: type[BaseModel], **_kwargs: Any) -> BaseModel:
        if schema is RouteDecision:
            return RouteDecision(route="action", rationale="flag a well")
        raise AssertionError(f"unexpected schema {schema}")

    monkeypatch.setattr("wellground.agent.llm.complete_structured", fake_complete)
    result = build_graph().compile().invoke(
        {
            "question": "Flag 16A for review",
            "run_id": "test",
            "sql_evidence": [],
            "rag_evidence": [],
            "retry_count": 0,
        }
    )
    assert result["response"].status == "refused"
    assert "not implemented" in result["response"].refusal_reason.lower()


def test_sql_route_uses_metric(monkeypatch: Any) -> None:
    def fake_complete(prompt: str, schema: type[BaseModel], **_kwargs: Any) -> BaseModel:
        if schema is RouteDecision:
            return RouteDecision(
                route="sql",
                rationale="metadata",
                sql_subquery="injector well",
            )
        if schema is SqlPlan:
            return SqlPlan(mode="metric", metric_id="well_role", params={"well_id": "16A"})
        if schema is SynthesisResult:
            return SynthesisResult(
                status="answered",
                claims=[Claim(text="16A is the injection_well.", source_ids=["E1"])],
            )
        raise AssertionError(f"unexpected schema {schema}")

    sql_evidence = SqlEvidence(
        query_id="q1",
        metric_id="well_role",
        sql="SELECT role FROM wells WHERE well_id = '16A'",
        row_count=1,
        rows=[{"well_id": "16A", "role": "injection_well"}],
        source="wells",
    )
    monkeypatch.setattr("wellground.agent.llm.complete_structured", fake_complete)
    monkeypatch.setattr("wellground.tools.sql.run_metric", lambda *a, **k: sql_evidence)

    result = build_graph().compile().invoke(
        {
            "question": "Which well is the injector?",
            "run_id": "test",
            "sql_evidence": [],
            "rag_evidence": [],
            "retry_count": 0,
        }
    )
    response = result["response"]
    assert response.status == "answered"
    assert response.evidence[0].kind == "sql"
    assert response.claims[0].source_ids == ["E1"]


def test_both_route_merges_sql_and_rag(monkeypatch: Any) -> None:
    def fake_complete(prompt: str, schema: type[BaseModel], **_kwargs: Any) -> BaseModel:
        if schema is RouteDecision:
            return RouteDecision(
                route="both",
                rationale="numbers and reports",
                sql_subquery="16B temperature",
                rag_subquery="circulation test procedure",
            )
        if schema is SqlPlan:
            return SqlPlan(
                mode="metric",
                metric_id="avg_temperature",
                params={"well_id": "16B"},
            )
        if schema is SynthesisResult:
            return SynthesisResult(
                status="answered",
                claims=[
                    Claim(text="16B temperature averaged 210.", source_ids=["E1"]),
                    Claim(
                        text="16A was hydraulically stimulated in April 2022.",
                        source_ids=["E2"],
                    ),
                ],
            )
        raise AssertionError(f"unexpected schema {schema}")

    sql_evidence = SqlEvidence(
        query_id="q1",
        metric_id="avg_temperature",
        sql="SELECT avg(temperature) AS avg_temperature FROM timeseries",
        row_count=1,
        rows=[{"well_id": "16B", "avg_temperature": 210.0}],
        source="gdr:2475065",
    )
    monkeypatch.setattr("wellground.agent.llm.complete_structured", fake_complete)
    monkeypatch.setattr("wellground.tools.sql.run_metric", lambda *a, **k: sql_evidence)
    monkeypatch.setattr(
        "wellground.tools.rag.search_docs", lambda query, **kwargs: [_rag_hit()]
    )

    result = build_graph().compile().invoke(
        {
            "question": "Compare production temp and cite the test procedure",
            "run_id": "test",
            "sql_evidence": [],
            "rag_evidence": [],
            "retry_count": 0,
        }
    )
    response = result["response"]
    assert response.status == "answered"
    assert response.route == "both"
    kinds = {item.kind for item in response.evidence}
    assert kinds == {"sql", "rag"}
    assert response.evidence[0].evidence_id == "E1"
    assert response.evidence[1].evidence_id == "E2"

