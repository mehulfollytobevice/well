"""Fireworks LLM client (OpenAI-compatible) with structured JSON output."""

from __future__ import annotations

import json
from typing import TypeVar, get_origin

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


def _parse_json_container(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _coerce_null_collection_fields(payload: dict[str, object], schema: type[BaseModel]) -> dict[str, object]:
    """LLMs often emit JSON null for empty lists/dicts; Pydantic will not apply defaults."""
    coerced = dict(payload)
    for name, field in schema.model_fields.items():
        origin = get_origin(field.annotation)
        if origin in {list, dict} and name in coerced:
            coerced[name] = _parse_json_container(coerced[name])
        if coerced.get(name, "MISSING") is not None:
            continue
        if origin is list:
            coerced[name] = []
        elif origin is dict:
            coerced[name] = {}
    return coerced


def _normalize_structured_payload(
    payload: dict[str, object], schema: type[BaseModel]
) -> dict[str, object]:
    """Unwrap schema-echo / titled wrappers into a Pydantic instance dict."""
    data = dict(payload)
    fields = schema.model_fields
    title = schema.__name__
    nested = data.get(title)
    if isinstance(nested, dict) and any(key in nested for key in fields) and not any(
        key in data for key in fields
    ):
        data = dict(nested)
    props = data.get("properties")
    if isinstance(props, dict) and any(key in props for key in fields) and not any(
        key in data for key in fields
    ):
        data = dict(props)
    name = data.get("name")
    if (
        isinstance(name, str)
        and name in fields
        and name not in data
        and "value" in data
    ):
        data[name] = data["value"]
    return _coerce_null_collection_fields(data, schema)


def _instance_hint(schema: type[BaseModel]) -> str:
    keys = ", ".join(schema.model_fields)
    example: dict[str, object] = {}
    for name, field in schema.model_fields.items():
        origin = get_origin(field.annotation)
        if origin is dict:
            example[name] = {}
        elif origin is list:
            example[name] = []
        else:
            example[name] = None
    return (
        f"Return a filled JSON instance only, not a JSON Schema. "
        f"Use these keys: {keys}. Nested objects must be JSON objects, not strings. "
        f"Example shape: {json.dumps(example)}. "
        'Do not emit "name", "type", "title", or "properties".'
    )


def complete_structured(prompt: str, schema: type[T], *, system: str | None = None) -> T:
    """Ask the model to return JSON matching `schema`."""
    settings = get_settings()
    full_prompt = (
        f"{prompt}\n\n"
        f"{_instance_hint(schema)}\n"
        "Do not include markdown or commentary."
    )
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": full_prompt})
    response = _client().chat.completions.create(
        model=settings.wellground_llm_model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned an empty response")
    parsed: object = json.loads(_strip_fences(content))
    if isinstance(parsed, dict):
        parsed = _normalize_structured_payload(parsed, schema)
    return schema.model_validate(parsed)
