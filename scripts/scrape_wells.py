#!/usr/bin/env python3
"""Scrape Utah FORGE well metadata into data/seed/wells.csv."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

DASHBOARD_URL = "https://utahforge.com/project-data-dashboard/"
GDR_GPS_URL = (
    "https://gdr.openei.org/files/1358/Utah%20FORGE%20Well%20and%20Seismic%20Locations.csv"
)
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "seed" / "wells.csv"

WELL_ID_ALIASES = {
    "16A(78)-32": "16A",
    "16B(78)-32": "16B",
    "56-32": "56-32",
    "68-32": "68-32",
    "58-32": "58-32",
    "78-32": "78-32",
    "78B-32": "78B-32",
}

GDR_WELL_KEYS = {
    "16A": "16A-32-WELL",
    "56-32": "56-32-WELL",
    "58-32": "58-32-WELL",
    "78-32": "78-32-WELL",
    "78B-32": "78B-32-WELL",
}

WIKI_ENRICHMENT = {
    "16A": {
        "tvd_ft": 8559,
        "lat": 38.504013,
        "lon": -112.896407,
        "notes_extra": "Highly deviated injection well; 65° from vertical; stimulated Apr 2022.",
    },
    "16B": {
        "tvd_ft": 8262,
        "lat": 38.504268,
        "lon": -112.896386,
        "notes_extra": "Production well drilled ~300 ft above and parallel to 16A; stimulated 2024.",
    },
}


@dataclass
class WellRecord:
    well_id: str
    name: str
    role: str
    md_ft: int | None = None
    tvd_ft: int | None = None
    lat: float | None = None
    lon: float | None = None
    notes: str = ""
    extras: list[str] = field(default_factory=list)


def fetch_text(url: str) -> str:
    result = subprocess.run(
        ["curl", "-sL", "--max-time", "60", url],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_depth_ft(text: str, label: str) -> int | None:
    pattern = rf"([\d,]+(?:\.\d+)?)\s*ft\s*{label}"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        approximate = re.search(rf"~([\d,]+(?:\.\d+)?)\s*ft\s*{label}", text, flags=re.IGNORECASE)
        if not approximate:
            return None
        match = approximate
    return int(float(match.group(1).replace(",", "")))


def parse_dashboard(html: str) -> list[WellRecord]:
    blocks = re.findall(
        r'<h2 class="dmpro-tooltip-title">\s*(.*?)\s*</h2>\s*'
        r'<div class="dmpro-tooltip-desc">\s*(.*?)\s*</div>',
        html,
        flags=re.DOTALL,
    )
    records: list[WellRecord] = []

    for raw_name, raw_desc in blocks:
        name = unescape(re.sub(r"\s+", " ", raw_name)).strip()
        desc_html = unescape(raw_desc)
        lines = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", line)).strip()
            for line in re.split(r"<br\s*/?>", desc_html, flags=re.IGNORECASE)
        ]
        lines = [line for line in lines if line]

        role_line = lines[0] if lines else ""
        role = role_line.lower().replace(" ", "_")
        desc = " ".join(lines)

        md_ft = parse_depth_ft(desc, "MD") or parse_depth_ft(desc, "TD")
        tvd_ft = parse_depth_ft(desc, "TVD")

        extras = []
        for token in ("DAS", "Seismometer", "Accelerometer"):
            if token.lower() in desc.lower():
                extras.append(token)

        base_id = WELL_ID_ALIASES.get(name, name)
        well_id = base_id
        if name == "58-32" and "water" in role_line.lower():
            well_id = "58-32-WW"

        notes_parts = [f"Source: {DASHBOARD_URL}#well-data"]
        if extras:
            notes_parts.append("Instrumentation: " + ", ".join(extras))

        records.append(
            WellRecord(
                well_id=well_id,
                name=name,
                role=role,
                md_ft=md_ft,
                tvd_ft=tvd_ft,
                notes="; ".join(notes_parts),
                extras=extras,
            )
        )

    return records


def load_gdr_coords(csv_text: str) -> dict[str, tuple[float, float, float | None]]:
    rows = list(csv.reader(csv_text.splitlines()))
    data_rows = rows[3:] if len(rows) > 3 else rows
    coords: dict[str, tuple[float, float, float | None]] = {}

    for row in data_rows:
        if len(row) < 5 or not row[0]:
            continue
        point_id = row[0].strip()
        try:
            lat = float(row[3])
            lon = float(row[4].strip())
            elev = float(row[5]) if len(row) > 5 and row[5] else None
        except ValueError:
            continue
        coords[point_id] = (lat, lon, elev)

    well_coords: dict[str, tuple[float, float, float | None]] = {}
    for well_id, point_id in GDR_WELL_KEYS.items():
        if point_id in coords:
            well_coords[well_id] = coords[point_id]

    if "68-32" not in well_coords:
        pad_points = [coords[k] for k in coords if k.startswith("68-32-") and "WELL" not in k]
        if pad_points:
            lat = sum(p[0] for p in pad_points) / len(pad_points)
            lon = sum(p[1] for p in pad_points) / len(pad_points)
            elev_vals = [p[2] for p in pad_points if p[2] is not None]
            elev = sum(elev_vals) / len(elev_vals) if elev_vals else None
            well_coords["68-32"] = (lat, lon, elev)

    return well_coords


def enrich_records(records: list[WellRecord], gdr_coords: dict[str, tuple[float, float, float | None]]) -> None:
    for record in records:
        wiki = WIKI_ENRICHMENT.get(record.well_id)
        if wiki:
            record.tvd_ft = record.tvd_ft or wiki.get("tvd_ft")
            record.lat = record.lat or wiki.get("lat")
            record.lon = record.lon or wiki.get("lon")
            if wiki.get("notes_extra"):
                record.notes = f"{record.notes}; {wiki['notes_extra']}"

        if record.well_id in gdr_coords and record.lat is None:
            lat, lon, _elev = gdr_coords[record.well_id]
            record.lat = lat
            record.lon = lon
            record.notes = f"{record.notes}; GPS: GDR submission 1358 (Dec 2021)"

        if record.well_id == "58-32-WW" and "58-32" in gdr_coords:
            lat, lon, _elev = gdr_coords["58-32"]
            record.lat = lat
            record.lon = lon
            record.notes = f"{record.notes}; Co-located with 58-32 pilot pad (approx)"


def write_csv(records: list[WellRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["well_id", "name", "role", "md_ft", "tvd_ft", "lat", "lon", "notes"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "well_id": record.well_id,
                    "name": record.name,
                    "role": record.role,
                    "md_ft": record.md_ft if record.md_ft is not None else "",
                    "tvd_ft": record.tvd_ft if record.tvd_ft is not None else "",
                    "lat": f"{record.lat:.6f}" if record.lat is not None else "",
                    "lon": f"{record.lon:.6f}" if record.lon is not None else "",
                    "notes": record.notes,
                }
            )


def main() -> int:
    print(f"Fetching dashboard: {DASHBOARD_URL}")
    dashboard_html = fetch_text(DASHBOARD_URL)
    records = parse_dashboard(dashboard_html)
    if not records:
        print("No wells parsed from dashboard.", file=sys.stderr)
        return 1

    print(f"Fetching GDR GPS coordinates: {GDR_GPS_URL}")
    gdr_csv = fetch_text(GDR_GPS_URL)
    gdr_coords = load_gdr_coords(gdr_csv)
    enrich_records(records, gdr_coords)

    write_csv(records, OUTPUT_PATH)
    print(f"Wrote {len(records)} wells to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
