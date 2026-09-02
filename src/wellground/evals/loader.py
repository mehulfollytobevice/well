"""Load golden JSONL from the repo evals/ directory."""

from __future__ import annotations

from pathlib import Path

from wellground.evals.schema import GoldCase, VerifierCase

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVALS_DIR = _REPO_ROOT / "evals"
DEFAULT_GOLDEN = DEFAULT_EVALS_DIR / "golden.jsonl"
DEFAULT_VERIFIER = DEFAULT_EVALS_DIR / "verifier_cases.jsonl"


def repo_root() -> Path:
    return _REPO_ROOT


def evals_dir() -> Path:
    return DEFAULT_EVALS_DIR


def _read_jsonl_lines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Eval file not found: {path}")
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def load_golden(path: Path | None = None) -> list[GoldCase]:
    target = path or DEFAULT_GOLDEN
    return [GoldCase.model_validate_json(line) for line in _read_jsonl_lines(target)]


def cases_for_tag(tag: str, path: Path | None = None) -> list[GoldCase]:
    return [case for case in load_golden(path) if tag in case.tags]


def load_verifier_cases(path: Path | None = None) -> list[VerifierCase]:
    target = path or DEFAULT_VERIFIER
    return [VerifierCase.model_validate_json(line) for line in _read_jsonl_lines(target)]
