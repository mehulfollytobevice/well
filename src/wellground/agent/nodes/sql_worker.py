"""SQL worker: pick a catalog metric or a constrained SELECT."""

from __future__ import annotations

from typing import Any

import duckdb

from wellground.agent import llm as llm
from wellground.agent.schemas import SqlPlan
from wellground.agent.state import AgentState
from wellground.semantic.catalog import catalog_prompt
from wellground.tools import sql as sql_tools

SQL_PROMPT = """You turn a question into a DuckDB lookup for Utah FORGE wells.

Prefer a catalog metric. Use mode=sql only if no metric fits.
Well ids look like 16A, 16B, 58-32. Circulation test dates: 2024-08-08 to 2024-09-05.
16A is the injector; 16B is the producer.
There is no field column — 16A/16B are well_id values. For "how many wells", use well_count.

If the question also asks to cite a daily report, procedure, or Step N pump rate, ignore that
part — RAG handles documents. Plan only the numeric/catalog lookup (for example avg_temperature
for 16B wellhead temperature). Do not SELECT wells.notes or invent report text in SQL.

Catalog:
{catalog}

Question: {question}
SQL subquery: {subquery}

If mode=metric, set metric_id and params (string values). Extra date params are optional.
If mode=sql, set a single SELECT over tables wells and/or timeseries using only listed columns.
"""


def sql_worker_node(state: AgentState) -> dict[str, Any]:
    decision = state["route_decision"]
    subquery = (decision.sql_subquery if decision else None) or state["question"]
    plan = llm.complete_structured(
        SQL_PROMPT.format(
            catalog=catalog_prompt(),
            question=state["question"],
            subquery=subquery,
        ),
        SqlPlan,
    )
    try:
        if plan.mode == "metric":
            if not plan.metric_id:
                raise ValueError("metric mode requires metric_id")
            evidence = sql_tools.run_metric(plan.metric_id, plan.params)
        else:
            if not plan.sql:
                raise ValueError("sql mode requires sql")
            evidence = sql_tools.run_sql_select(plan.sql)
    except (KeyError, ValueError, duckdb.Error):
        return {"sql_evidence": []}
    return {"sql_evidence": [evidence]}
