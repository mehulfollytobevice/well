"""Layer A: live router eval (Fireworks). Skips when FIREWORKS_API_KEY is unset."""

from __future__ import annotations

from typing import Any

import pytest

from wellground.agent.nodes.router import router_node
from wellground.evals.graders import grade_route
from wellground.evals.loader import cases_for_tag
from wellground.evals.schema import GoldCase

pytestmark = pytest.mark.live

# Known misses on the current router prompt/model. strict=False → XPASS if they start passing.
_XFAIL_ROUTER = {
    "sql-58-32-role": "router often classifies 58-32 catalog lookups as rag",
}


def _router_cases() -> list[Any]:
    params: list[Any] = []
    for case in cases_for_tag("router"):
        marks = []
        reason = _XFAIL_ROUTER.get(case.id)
        if reason:
            marks.append(pytest.mark.xfail(reason=reason, strict=False))
        params.append(pytest.param(case, id=case.id, marks=marks))
    return params


@pytest.mark.parametrize("gold", _router_cases())
def test_router_live(gold: GoldCase, require_fireworks_key: None) -> None:
    result = router_node({"question": gold.question, "run_id": f"eval-{gold.id}"})
    decision = result["route_decision"]
    graded = grade_route(decision, gold)
    assert graded.passed, graded.message
