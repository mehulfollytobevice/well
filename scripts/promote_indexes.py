#!/usr/bin/env python3
"""Copy local processed indexes into data/release/ for deploy commits."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data/processed"
DEFAULT_TARGET = PROJECT_ROOT / "data/release"

SOURCE_DOIS = [
    {"label": "Extended circulation time series", "doi": "10.15121/2475065"},
    {"label": "Circulation daily reports", "doi": "10.15121/2455019"},
    {"label": "Injection and production test reports", "doi": "10.15121/2473673"},
    {"label": "Well GPS metadata", "doi": "10.15121/1838418"},
]

ARTIFACTS = (
    ("forge.duckdb", "file"),
    ("chroma", "dir"),
    ("bm25", "dir"),
)


def _copy_artifact(source_root: Path, target_root: Path, name: str, kind: str) -> None:
    src = source_root / name
    dst = target_root / name
    if not src.exists():
        raise FileNotFoundError(f"Missing source artifact: {src}")
    if kind == "file":
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def promote(*, source: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    for name, kind in ARTIFACTS:
        _copy_artifact(source, target, name, kind)

    manifest = {
        "promoted_at": datetime.now(UTC).isoformat(),
        "source_dir": str(source.relative_to(PROJECT_ROOT)),
        "artifacts": [name for name, _ in ARTIFACTS],
        "source_dois": SOURCE_DOIS,
        "provenance": "data/PROVENANCE.md",
    }
    manifest_path = target / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    manifest = promote(source=args.source.resolve(), target=args.target.resolve())
    print(f"Promoted indexes to {args.target.resolve()}")
    print(f"Wrote {manifest}")


if __name__ == "__main__":
    main()
