"""Shared Pydantic models for the agent, tools, and evals."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SqlEvidence(BaseModel):
    kind: Literal["sql"] = "sql"
    evidence_id: str = ""
    query_id: str
    metric_id: str | None = None
    sql: str
    row_count: int
    rows: list[dict[str, object]]
    source: str


class RagEvidence(BaseModel):
    kind: Literal["rag"] = "rag"
    evidence_id: str = ""
    chunk_id: str
    doc_id: str
    title: str
    page: int
    excerpt: str
    well_ids: list[str]
    score: float
    section: str = ""


Evidence = SqlEvidence | RagEvidence


class RouteDecision(BaseModel):
    route: Literal["sql", "rag", "both", "action"]
    rationale: str
    sql_subquery: str | None = None
    rag_subquery: str | None = None


class SqlPlan(BaseModel):
    mode: Literal["metric", "sql"]
    metric_id: str | None = None
    params: dict[str, str] = Field(default_factory=dict)
    sql: str | None = None


class Claim(BaseModel):
    text: str
    source_ids: list[str]


class SynthesisResult(BaseModel):
    status: Literal["answered", "refused", "needs_clarification"]
    claims: list[Claim] = Field(default_factory=list)
    refusal_reason: str | None = None


class AgentResponse(BaseModel):
    status: Literal["answered", "refused", "needs_clarification"]
    route: str
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    refusal_reason: str | None = None
    verifier_notes: str | None = None
