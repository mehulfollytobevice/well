"""FastAPI endpoint tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from wellground.agent.schemas import AgentResponse, Claim, RagEvidence
from wellground.api.app import create_app
from wellground.config import get_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("WELLGROUND_DUCKDB_PATH", "data/release/forge.duckdb")
    monkeypatch.setenv("WELLGROUND_CHROMA_PATH", "data/release/chroma")
    monkeypatch.setenv("WELLGROUND_BM25_PATH", "data/release/bm25")
    get_settings.cache_clear()
    return TestClient(create_app())


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["indexes_ready"] is True


def test_health_missing_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WELLGROUND_DUCKDB_PATH", "data/release/missing.duckdb")
    monkeypatch.setenv("WELLGROUND_CHROMA_PATH", "data/release/missing-chroma")
    monkeypatch.setenv("WELLGROUND_BM25_PATH", "data/release/missing-bm25")
    get_settings.cache_clear()
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 503


def test_ask_returns_agent_response(client: TestClient) -> None:
    mock_response = AgentResponse(
        status="answered",
        route="rag",
        claims=[Claim(text="Peak flow was reported.", source_ids=["E1"])],
        evidence=[
            RagEvidence(
                evidence_id="E1",
                chunk_id="c1",
                doc_id="d1",
                title="Daily report",
                page=3,
                excerpt="Peak flow 42 gpm",
                well_ids=["16A"],
                score=0.9,
            )
        ],
    )
    with patch("wellground.api.app.run_agent", return_value=mock_response):
        response = client.post("/api/ask", json={"question": "What was peak flow?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["route"] == "rag"
    assert payload["claims"][0]["text"] == "Peak flow was reported."


def test_ask_requires_api_key_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WELLGROUND_DUCKDB_PATH", "data/release/forge.duckdb")
    monkeypatch.setenv("WELLGROUND_CHROMA_PATH", "data/release/chroma")
    monkeypatch.setenv("WELLGROUND_BM25_PATH", "data/release/bm25")
    monkeypatch.setenv("ASK_API_KEY", "secret-token")
    get_settings.cache_clear()
    client = TestClient(create_app())

    denied = client.post("/api/ask", json={"question": "hello"})
    assert denied.status_code == 401

    mock_response = AgentResponse(status="refused", route="rag", claims=[], evidence=[])
    with patch("wellground.api.app.run_agent", return_value=mock_response):
        allowed = client.post(
            "/api/ask",
            json={"question": "hello"},
            headers={"Authorization": "Bearer secret-token"},
        )
    assert allowed.status_code == 200
