"""Tests for WellCatalog pattern building."""

from __future__ import annotations

from pathlib import Path

from wellground.retrieval.well_catalog import WellCatalog, WellRecord

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_from_csv_loads_all_utah_forge_wells() -> None:
    catalog = WellCatalog.from_csv(PROJECT_ROOT / "data/seed/wells.csv")
    assert len(catalog.wells) == 8
    assert {well.well_id for well in catalog.wells} == {
        "16A",
        "16B",
        "56-32",
        "68-32",
        "58-32",
        "58-32-WW",
        "78-32",
        "78B-32",
    }


def test_longest_name_wins_for_shared_substrings() -> None:
    catalog = WellCatalog.from_records(
        (
            WellRecord("16A", "16A(78)-32"),
            WellRecord("16B", "16B(78)-32"),
        )
    )

    assert catalog.find_in_text("Operations on 16A(78)-32 were stable") == ["16A"]
    assert catalog.find_in_text("Both 16A and 16B were online") == ["16A", "16B"]
