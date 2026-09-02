"""Golden-set and verifier-eval schemas for Layer A component tests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wellground.agent.schemas import AgentResponse, Evidence

ComponentTag = Literal["router", "sql_plan", "sql_exec", "rag"]
RouteName = Literal["sql", "rag", "both", "action"]


class GoldCase(BaseModel):
    """One golden question. Tags select which component tests run it."""

    id: str
    question: str
    tags: list[ComponentTag]
    expected_route: RouteName | None = None
    expected_sql_metric: str | None = None
    expected_sql_params: dict[str, str] = Field(default_factory=dict)
    gold_sql_column: str | None = None
    gold_sql_value: float | int | str | None = None
    tolerance: float = 1.0
    rag_query: str | None = None
    gold_doc_id: str | None = None
    gold_page: int | None = None
    gold_well_ids: list[str] = Field(default_factory=list)
    notes: str = ""

    model_config = {"extra": "ignore"}

    def retrieval_query(self) -> str:
        return self.rag_query or self.question

    @model_validator(mode="after")
    def _require_fields_for_tags(self) -> GoldCase:
        if not self.tags:
            raise ValueError(f"{self.id}: tags must be non-empty")
        if "router" in self.tags and self.expected_route is None:
            raise ValueError(f"{self.id}: router tag requires expected_route")
        if ("sql_plan" in self.tags or "sql_exec" in self.tags) and not self.expected_sql_metric:
            raise ValueError(f"{self.id}: sql_plan/sql_exec requires expected_sql_metric")
        if "sql_exec" in self.tags and (not self.gold_sql_column or self.gold_sql_value is None):
            raise ValueError(f"{self.id}: sql_exec requires gold_sql_column and gold_sql_value")
        if "rag" in self.tags and (not self.gold_doc_id or self.gold_page is None):
            raise ValueError(f"{self.id}: rag tag requires gold_doc_id and gold_page")
        return self


class VerifierCase(BaseModel):
    """Synthetic verifier input: expected pass/fail plus an AgentResponse."""

    id: str
    expected_pass: bool
    response: AgentResponse
    evidence: list[Evidence] | None = None
    notes: str = ""

    model_config = {"extra": "ignore"}
