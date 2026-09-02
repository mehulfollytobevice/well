"""Layer A: deterministic verifier cases (no LLM, no indexes)."""

from __future__ import annotations

import pytest

from wellground.evals.graders import grade_verifier
from wellground.evals.loader import load_verifier_cases
from wellground.evals.schema import VerifierCase

_CASES = load_verifier_cases()


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.id)
def test_verifier_case(case: VerifierCase) -> None:
    result = grade_verifier(
        case.response,
        case.expected_pass,
        evidence=case.evidence,
        case_id=case.id,
    )
    assert result.passed, result.message
