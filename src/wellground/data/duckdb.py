"""DuckDB helpers: connect to forge.duckdb and (re)build it from seed/raw files."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd  # type: ignore[import-untyped]

from wellground.config import get_settings

ALLOWED_TABLES = frozenset({"wells", "timeseries"})
DEFAULT_XLSX_NAME = (
    "Extended Circulation Test Data 08082024 to 09052024 (30 sec increment).xlsx"
)


def connect(
    db_path: Path | str | None = None,
    *,
    read_only: bool = True,
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection. Use `db_path=':memory:'` in tests."""
    if db_path == ":memory:":
        return duckdb.connect(":memory:")
    path = Path(db_path) if db_path is not None else get_settings().wellground_duckdb_path
    if not path.exists():
        raise FileNotFoundError(
            f"DuckDB file not found: {path}. Run scripts/setup_database.py first."
        )
    return duckdb.connect(str(path), read_only=read_only)


def build_database(
    *,
    db_path: Path | None = None,
    wells_csv: Path | None = None,
    timeseries_xlsx: Path | None = None,
) -> Path:
    """Load wells.csv + circulation-test XLSX into DuckDB. Returns the db path."""
    settings = get_settings()
    data_dir = settings.wellground_data_dir
    db_path = db_path or settings.wellground_duckdb_path
    wells_csv = wells_csv or data_dir / "seed" / "wells.csv"
    timeseries_xlsx = timeseries_xlsx or data_dir / "raw" / "timeseries" / DEFAULT_XLSX_NAME

    db_path.parent.mkdir(parents=True, exist_ok=True)

    df_wells = pd.read_csv(wells_csv)
    timeseries = _load_timeseries(timeseries_xlsx)

    conn = duckdb.connect(str(db_path))
    conn.register("df_wells", df_wells)
    conn.register("timeseries_src", timeseries)
    conn.execute("CREATE OR REPLACE TABLE wells AS SELECT * FROM df_wells")
    conn.execute(
        """
        CREATE OR REPLACE TABLE timeseries AS
        SELECT
            ts::TIMESTAMP AS ts,
            well_id::VARCHAR AS well_id,
            flow_rate::DOUBLE AS flow_rate,
            pressure::DOUBLE AS pressure,
            temperature::DOUBLE AS temperature,
            source::VARCHAR AS source
        FROM timeseries_src
        """
    )
    conn.close()
    return db_path


def _load_timeseries(xlsx_path: Path) -> pd.DataFrame:
    raw = pd.read_excel(xlsx_path, header=None, skiprows=4)
    raw.columns = [
        "ts",
        "pressure_16b",
        "flow_16b_1",
        "flow_16b_2",
        "temp_16b",
        "flow_sep_1",
        "flow_sep_2",
        "flow_sep_total",
        "pressure_16a",
        "pump_rate_liberty",
        "pressure_liberty",
    ]
    raw["ts"] = pd.to_datetime(raw["ts"], errors="coerce")
    raw = raw.dropna(subset=["ts"])
    num_cols = [c for c in raw.columns if c != "ts"]
    raw[num_cols] = raw[num_cols].apply(pd.to_numeric, errors="coerce")

    well_16b = raw[["ts", "pressure_16b", "temp_16b", "flow_16b_1"]].copy()
    well_16b["well_id"] = "16B"
    well_16b = well_16b.rename(
        columns={
            "pressure_16b": "pressure",
            "temp_16b": "temperature",
            "flow_16b_1": "flow_rate",
        }
    )

    well_16a = raw[["ts", "pressure_16a"]].copy()
    well_16a["well_id"] = "16A"
    well_16a = well_16a.rename(columns={"pressure_16a": "pressure"})
    well_16a["temperature"] = pd.NA
    well_16a["flow_rate"] = pd.NA

    frame = pd.concat([well_16b, well_16a], ignore_index=True)
    frame["source"] = "gdr:2475065 raw uncorrected"
    return frame
