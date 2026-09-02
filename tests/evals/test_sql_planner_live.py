"""Layer A: live SQL planner eval (Fireworks). Captures SqlPlan without querying DuckDB."""

from __future__ import annotations

from typing import Any

import pytest

from wellground.agent.nodes.sql_worker import sql_worker_node
from wellground.agent.schemas import RouteDecision, SqlEvidence, SqlPlan
from wellground.evals.graders import grade_sql_plan
from wellground.evals.loader import cases_for_tag
from wellground.evals.schema import GoldCase

pytestmark = pytest.mark.live

_CASES = cases_for_tag("sql_plan")


def _stub_evidence() -> SqlEvidence:
    return SqlEvidence(
        query_id="eval-stub",
        sql="SELECT 1",
        row_count=0,
        rows=[],
        source="eval-stub",
    )


@pytest.mark.parametrize("gold", _CASES, ids=lambda c: c.id)
def test_sql_planner_live(
    gold: GoldCase,
    require_fireworks_key: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[SqlPlan] = []

    def capture_metric(
        metric_id: str,
        params: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> SqlEvidence:
        captured.append(
            SqlPlan(
                mode="metric",
                metric_id=metric_id,
                params={str(k): str(v) for k, v in (params or {}).items()},
            )
        )
        return _stub_evidence()

    def capture_sql(sql: str, **_kwargs: Any) -> SqlEvidence:
        captured.append(SqlPlan(mode="sql", sql=sql))
        return _stub_evidence()

    monkeypatch.setattr(
        "wellground.agent.nodes.sql_worker.sql_tools.run_metric", capture_metric
    )
    monkeypatch.setattr(
        "wellground.agent.nodes.sql_worker.sql_tools.run_sql_select", capture_sql
    )

    route = gold.expected_route if gold.expected_route in {"sql", "both"} else "sql"
    sql_subquery = gold.question
    if gold.expected_route == "both" and gold.expected_sql_metric:
        params = ", ".join(f"{k}={v}" for k, v in gold.expected_sql_params.items())
        sql_subquery = f"{gold.expected_sql_metric} {params}".strip()
    state = {
        "question": gold.question,
        "run_id": f"eval-{gold.id}",
        "route_decision": RouteDecision(
            route=route,
            rationale="layer-a sql planner eval",
            sql_subquery=sql_subquery,
        ),
    }
    sql_worker_node(state)
    assert captured, f"{gold.id} sql_plan: worker did not call run_metric or run_sql_select"
    graded = grade_sql_plan(captured[-1], gold)
    assert graded.passed, graded.message
