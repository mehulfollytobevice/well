"""Tests for deterministic citation verification."""

from __future__ import annotations

from wellground.agent.nodes.verifier import verify_response
from wellground.agent.schemas import AgentResponse, Claim, RagEvidence, SqlEvidence


def _rag(evidence_id: str = "E1") -> RagEvidence:
    return RagEvidence(
        evidence_id=evidence_id,
        chunk_id="doc#p001#c00",
        doc_id="doc",
        title="Daily report",
        page=1,
        excerpt="16A was hydraulically stimulated in April 2022.",
        well_ids=["16A"],
        score=0.1,
    )


def test_verify_accepts_grounded_claim() -> None:
    response = AgentResponse(
        status="answered",
        route="rag",
        claims=[
            Claim(
                text="16A was hydraulically stimulated in April 2022.",
                source_ids=["E1"],
            )
        ],
        evidence=[_rag()],
    )
    ok, notes = verify_response(response)
    assert ok
    assert notes == ""


def test_verify_rejects_unknown_source_id() -> None:
    response = AgentResponse(
        status="answered",
        route="rag",
        claims=[Claim(text="16A was stimulated in 2022.", source_ids=["E99"])],
        evidence=[_rag()],
    )
    ok, notes = verify_response(response)
    assert not ok
    assert "unknown ids" in notes


def test_verify_empty_evidence_forces_fail() -> None:
    response = AgentResponse(status="answered", route="rag", claims=[], evidence=[])
    ok, notes = verify_response(response)
    assert not ok
    assert "No evidence" in notes


def test_sql_claim_grounded_in_rows() -> None:
    sql = SqlEvidence(
        evidence_id="E1",
        query_id="q1",
        metric_id="well_role",
        sql="SELECT role FROM wells WHERE well_id = '16A'",
        row_count=1,
        rows=[{"well_id": "16A", "role": "injection_well"}],
        source="wells",
    )
    response = AgentResponse(
        status="answered",
        route="sql",
        claims=[Claim(text="16A is an injection_well.", source_ids=["E1"])],
        evidence=[sql],
    )
    ok, notes = verify_response(response)
    assert ok, notes
