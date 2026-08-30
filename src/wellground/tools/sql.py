"""SQL tools over forge.duckdb — curated metrics first, constrained SELECT fallback."""

from __future__ import annotations
# imports
import re
import uuid
from pathlib import Path
from typing import Any

# local imports
from wellground.agent.schemas import SqlEvidence
from wellground.data.duckdb import ALLOWED_TABLES, connect
from wellground.semantic.catalog import FORMAT_KEYS, get_metric, render_sql

# let's define some ground rules
MAX_EVIDENCE_ROWS = 50
SQL_ROW_LIMIT = 500
_FORBIDDEN = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "attach",
    "copy",
    "export",
    "pragma",
    "call",
    "replace",
    "truncate",
)


def run_metric(
    metric_id: str,
    params: dict[str, Any] | None = None,
    *,
    db_path: Path | str | None = None,
) -> SqlEvidence:
    metric = get_metric(metric_id)
    bound = {**metric.defaults, **(params or {})}
    sql = render_sql(metric, bound)
    bind = {key: bound[key] for key in metric.params if key in bound and key not in FORMAT_KEYS}
    return _execute(sql, bind, metric_id=metric.id, source=metric.source, db_path=db_path)


def run_sql_select(
    sql: str,
    *,
    db_path: Path | str | None = None,
) -> SqlEvidence:
    safe_sql = _validate_select(sql)
    return _execute(safe_sql, {}, metric_id=None, source="duckdb", db_path=db_path)


def _execute(
    sql: str,
    bind: dict[str, Any],
    *,
    metric_id: str | None,
    source: str,
    db_path: Path | str | None,
) -> SqlEvidence:
    conn = connect(db_path)
    try:
        result = conn.execute(sql, bind) if bind else conn.execute(sql)
        columns = [col[0] for col in result.description]
        fetched = result.fetchmany(MAX_EVIDENCE_ROWS)
    finally:
        conn.close()
    rows = [_row_to_dict(columns, row) for row in fetched]
    return SqlEvidence(
        query_id=str(uuid.uuid4()),
        metric_id=metric_id,
        sql=sql,
        row_count=len(rows),
        rows=rows,
        source=source,
    )


def _row_to_dict(columns: list[str], row: tuple[object, ...]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in zip(columns, row, strict=True):
        if hasattr(value, "isoformat"):
            out[key] = value.isoformat()  # type: ignore[union-attr]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        else:
            out[key] = str(value)
    return out


def _validate_select(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise ValueError("Only a single SQL statement is allowed")
    lower = stripped.lower()
    if not lower.startswith("select"):
        raise ValueError("Only SELECT queries are allowed")
    for word in _FORBIDDEN:
        if re.search(rf"\b{word}\b", lower):
            raise ValueError(f"SQL keyword not allowed: {word}")
    tables = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", lower)
    if not tables:
        raise ValueError("SELECT must reference a table")
    for table in tables:
        name = table.split(".")[-1]
        if name not in ALLOWED_TABLES:
            raise ValueError(f"Table not allowed: {name}. Allowed: {sorted(ALLOWED_TABLES)}")
    return f"SELECT * FROM ({stripped}) AS q LIMIT {SQL_ROW_LIMIT}"
