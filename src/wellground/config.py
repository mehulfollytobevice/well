"""App settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fireworks_api_key: str = ""
    wellground_llm_model: str = "accounts/fireworks/models/gpt-oss-120b"
    wellground_env: str = "development"
    wellground_log_level: str = "INFO"
    wellground_data_dir: Path = Path("./data")
    wellground_duckdb_path: Path = Path("./data/processed/forge.duckdb")
    wellground_chroma_path: Path = Path("./data/processed/chroma")
    wellground_bm25_path: Path = Path("./data/processed/bm25")


@lru_cache
def get_settings() -> Settings:
    return Settings()
