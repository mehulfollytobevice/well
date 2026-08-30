"""Tests for curated metrics and constrained SQL."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from wellground.semantic.catalog import get_metric, list_metrics
from wellground.tools.sql import run_metric, run_sql_select


def _make_db(path: Path) -> Path:
    conn = duckdb.connect(str(path))
    conn.execute("CREATE TABLE wells (well_id VARCHAR, name VARCHAR, role VARCHAR, md_ft INTEGER)")
    conn.execute(
        "INSERT INTO wells VALUES ('16A', '16A(78)-32', 'injection_well', 10987)"
    )
    conn.execute(
        """
        CREATE TABLE timeseries (
            ts TIMESTAMP, well_id VARCHAR, flow_rate DOUBLE,
            pressure DOUBLE, temperature DOUBLE, source VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO timeseries VALUES
            ('2024-08-10 00:00:00', '16B', 10, 100, 200, 'test'),
            ('2024-08-11 00:00:00', '16B', 20, 110, 220, 'test')
        """
    )
    conn.close()
    return path


def test_catalog_has_core_metrics() -> None:
    expected = {
        "well_role",
        "well_count",
        "list_wells",
        "avg_temperature",
        "avg_pressure",
        "avg_flow_rate",
        "timeseries_peak",
    }
    ids = {metric.id for metric in list_metrics()}
    assert expected <= ids
    assert get_metric("well_role").params == ("well_id",)


def test_run_metric_well_count(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "forge.duckdb")
    evidence = run_metric("well_count", {}, db_path=db)
    assert evidence.rows[0]["well_count"] == 1


def test_run_metric_list_wells(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "forge.duckdb")
    evidence = run_metric("list_wells", {}, db_path=db)
    assert evidence.row_count == 1
    assert evidence.rows[0]["well_id"] == "16A"


def test_run_metric_well_role(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "forge.duckdb")
    evidence = run_metric("well_role", {"well_id": "16A"}, db_path=db)
    assert evidence.metric_id == "well_role"
    assert evidence.row_count == 1
    assert evidence.rows[0]["role"] == "injection_well"
    assert evidence.query_id


def test_run_metric_avg_temperature(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "forge.duckdb")
    evidence = run_metric(
        "avg_temperature",
        {"well_id": "16B", "start_ts": "2024-08-01", "end_ts": "2024-09-01"},
        db_path=db,
    )
    assert evidence.rows[0]["avg_temperature"] == 210.0


def test_run_sql_select_allowlist(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "forge.duckdb")
    evidence = run_sql_select("SELECT well_id, role FROM wells", db_path=db)
    assert evidence.row_count == 1
    assert "LIMIT 500" in evidence.sql


def test_run_sql_select_rejects_drop() -> None:
    with pytest.raises(ValueError, match="SELECT"):
        run_sql_select("DROP TABLE wells")


def test_run_sql_select_rejects_unknown_table() -> None:
    with pytest.raises(ValueError, match="Table not allowed"):
        run_sql_select("SELECT * FROM secrets")
