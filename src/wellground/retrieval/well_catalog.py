"""Well registry for matching well ids in unstructured text."""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WELLS_CSV = Path("data/seed/wells.csv")


@dataclass(frozen=True)
class WellRecord:
    well_id: str
    name: str


@dataclass
class WellCatalog:
    """Searchable catalog of wells loaded from seed data (e.g. wells.csv)."""

    wells: tuple[WellRecord, ...]
    _rules: tuple[tuple[re.Pattern[str], str], ...]

    @classmethod
    def from_csv(cls, path: Path | str = DEFAULT_WELLS_CSV) -> WellCatalog:
        path = Path(path)
        with path.open(newline="", encoding="utf-8") as handle:
            rows = csv.DictReader(handle)
            wells = tuple(
                WellRecord(well_id=row["well_id"].strip(), name=row["name"].strip())
                for row in rows
                if row.get("well_id", "").strip()
            )
        return cls.from_records(wells)

    @classmethod
    def from_records(cls, wells: tuple[WellRecord, ...] | list[WellRecord]) -> WellCatalog:
        records = tuple(wells)
        return cls(wells=records, _rules=_build_rules(records))

    def find_in_text(self, *texts: str) -> list[str]:
        """Return well_ids mentioned in the given strings, most specific first."""
        combined = " ".join(texts)
        found: list[str] = []
        for pattern, well_id in self._rules:
            if pattern.search(combined) and well_id not in found:
                found.append(well_id)
        return found


def _build_rules(wells: tuple[WellRecord, ...]) -> tuple[tuple[re.Pattern[str], str], ...]:
    name_counts = Counter(record.name.lower() for record in wells if record.name)

    rules: list[tuple[re.Pattern[str], str, int]] = []
    for record in wells:
        well_id = record.well_id
        name = record.name
        name_is_unique = bool(name) and name_counts[name.lower()] == 1

        if name_is_unique:
            rules.append((_compile_label_pattern(name), well_id, len(name)))

        # Always index the canonical well_id when it differs from a shared display name.
        if well_id and (not name_is_unique or well_id.lower() != name.lower()):
            rules.append((_compile_label_pattern(well_id), well_id, len(well_id)))

    rules.sort(key=lambda item: item[2], reverse=True)
    return tuple((pattern, well_id) for pattern, well_id, _length in rules)


def _compile_label_pattern(label: str) -> re.Pattern[str]:
    """Turn a well name or id into a regex that tolerates flexible spacing."""
    escaped = re.escape(label.strip())
    escaped = re.sub(r"\\\s+", r"\\s+", escaped)
    escaped = re.sub(r"\\-", r"[-\\s]?", escaped)

    if re.fullmatch(r"[\w.-]+", label.strip()):
        # Avoid matching a short id inside a longer one (e.g. 58-32 within 58-32-WW).
        pattern = rf"\b{escaped}\b(?![-\w])"
    else:
        pattern = escaped

    return re.compile(pattern, re.IGNORECASE)
