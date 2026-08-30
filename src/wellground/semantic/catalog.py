"""Load metrics.yaml and look up SQL templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

CATALOG_PATH = Path(__file__).with_name("metrics.yaml")
FORMAT_KEYS = frozenset({"column", "agg"})
ALLOWED_COLUMNS = frozenset({"flow_rate", "pressure", "temperature"})
ALLOWED_AGGS = frozenset({"MAX", "MIN"})


@dataclass(frozen=True)
class Metric:
    id: str
    description: str
    sql: str
    params: tuple[str, ...]
    defaults: dict[str, str]
    source: str


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Metric]:
    raw = yaml.safe_load(path.read_text()) or {}
    metrics_raw = raw.get("metrics") or {}
    catalog: dict[str, Metric] = {}
    for metric_id, spec in metrics_raw.items():
        defaults = {str(k): str(v) for k, v in (spec.get("defaults") or {}).items()}
        catalog[metric_id] = Metric(
            id=metric_id,
            description=spec.get("description", ""),
            sql=spec["sql"].strip(),
            params=tuple(spec.get("params") or ()),
            defaults=defaults,
            source=spec.get("source", ""),
        )
    return catalog


def list_metrics() -> list[Metric]:
    return list(load_catalog().values())


def get_metric(metric_id: str) -> Metric:
    catalog = load_catalog()
    if metric_id not in catalog:
        known = ", ".join(sorted(catalog)) or "(none)"
        raise KeyError(f"Unknown metric '{metric_id}'. Known: {known}")
    return catalog[metric_id]


def render_sql(metric: Metric, params: dict[str, Any]) -> str:
    """Fill `{column}` / `{agg}` placeholders after allowlisting."""
    sql = metric.sql
    if "{column}" not in sql and "{agg}" not in sql:
        return sql
    column = str(params.get("column", "temperature"))
    agg = str(params.get("agg", "MAX")).upper()
    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"column must be one of {sorted(ALLOWED_COLUMNS)}")
    if agg not in ALLOWED_AGGS:
        raise ValueError(f"agg must be one of {sorted(ALLOWED_AGGS)}")
    return sql.format(column=column, agg=agg)


def catalog_prompt() -> str:
    schema = (
        "Tables:\n"
        "- wells(well_id, name, role, md_ft, tvd_ft, lat, lon, notes) — "
        "16A/16B are well_ids, not field names; there is no field column\n"
        "- timeseries(ts, well_id, flow_rate, pressure, temperature, source)"
    )
    lines = [schema, "", "Metrics:"]
    for metric in list_metrics():
        params = ", ".join(metric.params) or "(none)"
        lines.append(f"- {metric.id}: {metric.description} [params: {params}]")
    return "\n".join(lines)
