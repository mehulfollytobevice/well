"""Layer A: SQL catalog metrics against the release DuckDB snapshot."""

from __future__ import annotations

from pathlib import Path

import pytest

from wellground.evals.graders import grade_sql_result
from wellground.evals.loader import cases_for_tag
from wellground.evals.schema import GoldCase
from wellground.tools.sql import run_metric

_CASES = cases_for_tag("sql_exec")


@pytest.mark.parametrize("gold", _CASES, ids=lambda c: c.id)
def test_sql_execution(gold: GoldCase, release_paths: dict[str, Path]) -> None:
    assert gold.expected_sql_metric is not None
    evidence = run_metric(
        gold.expected_sql_metric,
        gold.expected_sql_params,
        db_path=release_paths["duckdb"],
    )
    result = grade_sql_result(evidence, gold)
    assert result.passed, result.message
