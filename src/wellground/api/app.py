"""FastAPI application for WellGround agent."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from wellground.agent.graph import run_agent
from wellground.agent.schemas import AgentResponse
from wellground.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class HealthResponse(BaseModel):
    ok: bool
    indexes_ready: bool
    missing: list[str]


def _missing_indexes(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not settings.wellground_duckdb_path.exists():
        missing.append(str(settings.wellground_duckdb_path))
    for path in (settings.wellground_chroma_path, settings.wellground_bm25_path):
        if not path.exists() or not path.is_dir():
            missing.append(str(path))
    return missing


def verify_ask_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    expected = settings.ask_api_key
    if not expected:
        return
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def create_app() -> FastAPI:
    app = FastAPI(title="WellGround", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
        missing = _missing_indexes(settings)
        if missing:
            raise HTTPException(
                status_code=503,
                detail={"ok": False, "indexes_ready": False, "missing": missing},
            )
        return HealthResponse(ok=True, indexes_ready=True, missing=[])

    @app.post("/api/ask", response_model=AgentResponse)
    def ask(
        body: AskRequest,
        _: Annotated[None, Depends(verify_ask_api_key)],
    ) -> AgentResponse:
        return run_agent(body.question)

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, exc: Exception):
        from starlette.responses import JSONResponse

        if os.getenv("WELLGROUND_ENV", "development") == "production":
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        raise exc

    return app


app = create_app()
