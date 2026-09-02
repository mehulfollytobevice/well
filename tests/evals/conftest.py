"""Shared fixtures for Layer A evals. Never log API keys or settings dumps."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from wellground.config import get_settings
from wellground.retrieval.hybrid import HybridRetriever

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = REPO_ROOT / "data" / "release"


@pytest.fixture(scope="session")
def release_paths() -> dict[str, Path]:
    duckdb = RELEASE_DIR / "forge.duckdb"
    chroma = RELEASE_DIR / "chroma"
    bm25 = RELEASE_DIR / "bm25"
    if not duckdb.is_file():
        pytest.skip(f"Release DuckDB missing: {duckdb}")
    if not (bm25 / "chunks.jsonl").is_file():
        pytest.skip(f"Release BM25 index missing: {bm25}")
    if not chroma.is_dir():
        pytest.skip(f"Release Chroma index missing: {chroma}")
    return {"duckdb": duckdb, "chroma": chroma, "bm25": bm25, "root": RELEASE_DIR}


@pytest.fixture
def release_settings(
    monkeypatch: pytest.MonkeyPatch, release_paths: dict[str, Path]
) -> Iterator[None]:
    monkeypatch.setenv("WELLGROUND_DUCKDB_PATH", str(release_paths["duckdb"]))
    monkeypatch.setenv("WELLGROUND_CHROMA_PATH", str(release_paths["chroma"]))
    monkeypatch.setenv("WELLGROUND_BM25_PATH", str(release_paths["bm25"]))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def release_retriever(release_paths: dict[str, Path]) -> HybridRetriever:
    return HybridRetriever.load(
        bm25_dir=release_paths["bm25"],
        chroma_dir=release_paths["chroma"],
    )


@pytest.fixture
def require_fireworks_key() -> None:
    """Skip live LLM tests when no key is configured. Never print the value."""
    get_settings.cache_clear()
    if not get_settings().fireworks_api_key:
        pytest.skip("FIREWORKS_API_KEY not set")
