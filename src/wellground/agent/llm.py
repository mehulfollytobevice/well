"""Fireworks LLM client (OpenAI-compatible) with structured JSON output."""

from __future__ import annotations

import json
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from wellground.config import get_settings

T = TypeVar("T", bound=BaseModel)

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.fireworks_api_key:
        raise RuntimeError("FIREWORKS_API_KEY is not set")
    return OpenAI(api_key=settings.fireworks_api_key, base_url=FIREWORKS_BASE_URL)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    inner = [line for line in lines if not line.startswith("```")]
    return "\n".join(inner).strip()


def complete_structured(prompt: str, schema: type[T]) -> T:
    """Ask the model to return JSON matching `schema`."""
    settings = get_settings()
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        "Respond with a single JSON object that matches this schema. "
        "Do not include markdown or commentary.\n"
        f"{schema_json}"
    )
    response = _client().chat.completions.create(
        model=settings.wellground_llm_model,
        messages=[{"role": "user", "content": full_prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned an empty response")
    return schema.model_validate_json(_strip_fences(content))
