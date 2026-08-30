"""One JSON line per agent run (stderr)."""

from __future__ import annotations

import json
import sys
from typing import Any

from wellground.config import get_settings


def log_run(
    *,
    run_id: str,
    question: str,
    route: str,
    status: str,
    evidence_count: int,
    latency_ms: float,
) -> None:
    payload: dict[str, Any] = {
        "run_id": run_id,
        "route": route,
        "status": status,
        "evidence_count": evidence_count,
        "latency_ms": latency_ms,
        "model": get_settings().wellground_llm_model,
        "question": question,
    }
    print(json.dumps(payload), file=sys.stderr)
