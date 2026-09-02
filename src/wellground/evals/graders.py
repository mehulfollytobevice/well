"""Deterministic graders for Layer A component evals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wellground.agent.nodes.verifier import verify_response
from wellground.agent.schemas import (
    AgentResponse,
    Evidence,
    RagEvidence,
    RouteDecision,
    SqlEvidence,
    SqlPlan,
)
from wellground.evals.schema import GoldCase


@dataclass(frozen=True)
class GradeResult:
    passed: bool
    message: str


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def grade_route(decision: RouteDecision, gold: GoldCase) -> GradeResult:
    expected = gold.expected_route
    actual = decision.route
    if actual == expected:
        return GradeResult(True, "")
    return GradeResult(
        False,
        f"{gold.id} router: expected route {expected!r}, got {actual!r}",
    )


def grade_sql_plan(plan: SqlPlan, gold: GoldCase) -> GradeResult:
    expected_metric = gold.expected_sql_metric
    if plan.mode != "metric":
        return GradeResult(
            False,
            f"{gold.id} sql_plan: expected mode='metric' metric_id={expected_metric!r}, "
            f"got mode={plan.mode!r} sql={plan.sql!r}",
        )
    if plan.metric_id != expected_metric:
        return GradeResult(
            False,
            f"{gold.id} sql_plan: expected metric_id={expected_metric!r}, got {plan.metric_id!r}",
        )
    actual_params = {str(k): str(v) for k, v in (plan.params or {}).items()}
    for key, value in gold.expected_sql_params.items():
        got = actual_params.get(key)
        if got != str(value):
            return GradeResult(
                False,
                f"{gold.id} sql_plan: expected param {key}={value!r}, got {got!r} "
                f"(params={actual_params})",
            )
    return GradeResult(True, "")


def grade_sql_result(evidence: SqlEvidence, gold: GoldCase) -> GradeResult:
    column = gold.gold_sql_column
    if not column:
        return GradeResult(False, f"{gold.id} sql_exec: missing gold_sql_column")
    if not evidence.rows:
        return GradeResult(False, f"{gold.id} sql_exec: no rows returned")
    row = evidence.rows[0]
    if column not in row:
        return GradeResult(
            False,
            f"{gold.id} sql_exec: column {column!r} not in {list(row)}",
        )
    actual: Any = row[column]
    expected = gold.gold_sql_value
    if _is_number(expected) and _is_number(actual):
        delta = abs(float(actual) - float(expected))
        if delta <= gold.tolerance:
            return GradeResult(True, "")
        return GradeResult(
            False,
            f"{gold.id} sql_exec: {column}={actual!r} not within {gold.tolerance} of {expected!r}",
        )
    if actual == expected or str(actual) == str(expected):
        return GradeResult(True, "")
    return GradeResult(
        False,
        f"{gold.id} sql_exec: {column}={actual!r} != gold {expected!r}",
    )


def grade_retrieval(
    hits: list[RagEvidence],
    gold: GoldCase,
    *,
    top_k: int = 6,
) -> GradeResult:
    if not gold.gold_doc_id or gold.gold_page is None:
        return GradeResult(False, f"{gold.id} rag: missing gold_doc_id/gold_page")
    ranked = hits[:top_k]
    for hit in ranked:
        if hit.doc_id == gold.gold_doc_id and hit.page == gold.gold_page:
            return GradeResult(True, "")
    actual = [(hit.doc_id, hit.page) for hit in ranked]
    return GradeResult(
        False,
        f"{gold.id} rag: expected doc_id={gold.gold_doc_id!r} page={gold.gold_page} "
        f"in top-{top_k}; got {actual}",
    )


def grade_verifier(
    response: AgentResponse,
    expected_pass: bool,
    evidence: list[Evidence] | None = None,
    *,
    case_id: str = "",
) -> GradeResult:
    ok, notes = verify_response(response, evidence)
    prefix = f"{case_id} verifier: " if case_id else "verifier: "
    if ok == expected_pass:
        return GradeResult(True, "")
    return GradeResult(
        False,
        f"{prefix}expected_pass={expected_pass}, got {ok} ({notes or 'no notes'})",
    )
