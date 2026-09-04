"""Split parsed PDF pages into retrieval-sized chunks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import tiktoken

from wellground.retrieval.pdf_parser import PdfPage

DEFAULT_MAX_TOKENS = 600
DEFAULT_OVERLAP_TOKENS = 100


@dataclass
class Chunk:
    """One passage ready for embedding or BM25 indexing."""

    chunk_id: str
    doc_id: str
    title: str
    page: int
    text: str
    well_ids: list[str]
    token_count: int
    section: str = ""

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> Chunk:
        """Load a chunk from JSONL / index metadata, including older records."""
        well_ids_raw = row.get("well_ids") or []
        if isinstance(well_ids_raw, str):
            well_ids = [part for part in well_ids_raw.split(",") if part]
        else:
            well_ids = [str(item) for item in well_ids_raw]
        return cls(
            chunk_id=str(row["chunk_id"]),
            doc_id=str(row["doc_id"]),
            title=str(row["title"]),
            page=int(row["page"]),
            text=str(row["text"]),
            well_ids=well_ids,
            token_count=int(row.get("token_count") or 0),
            section=str(row.get("section") or ""),
        )


@lru_cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return the cl100k_base token count for a string."""
    return len(_encoding().encode(text))


def make_chunk_id(doc_id: str, page: int, index: int) -> str:
    """Stable id for citations, e.g. daily_reports/report#p001#c00."""
    return f"{doc_id}#p{page:03d}#c{index:02d}"


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split layout markdown into ``(section_name, body)`` pairs."""
    if not text.strip():
        return []

    sections: list[tuple[str, str]] = []
    current_name = ""
    current_lines: list[str] = []

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if not body:
            return
        name = current_name or "Body"
        sections.append((name, body))

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_name = line[3:].strip() or "Body"
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()
    return sections


def chunk_page(
    page: PdfPage,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split one page into section chunks, with token windows inside long sections."""
    chunks: list[Chunk] = []
    index = 0
    for section, body in split_sections(page.text):
        built = _chunks_for_section(
            page,
            section=section,
            body=body,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            start_index=index,
        )
        chunks.extend(built)
        index += len(built)
    return chunks


def chunk_pages(
    pages: list[PdfPage],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Chunk an in-memory list of pages."""
    chunks: list[Chunk] = []
    for page in pages:
        chunks.extend(
            chunk_page(page, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
        )
    return chunks


def load_pages_jsonl(path: Path) -> list[PdfPage]:
    """Load page records written by ``write_pages_jsonl``."""
    pages: list[PdfPage] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            pages.append(PdfPage(**row))
    return pages


def write_chunks_jsonl(chunks: list[Chunk], output_path: Path) -> None:
    """Save chunks as JSON Lines for inspection or downstream indexing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def load_chunks_jsonl(path: Path) -> list[Chunk]:
    """Load chunk records written by ``write_chunks_jsonl``."""
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            chunks.append(Chunk.from_mapping(row))
    return chunks


def _section_display_text(section: str, body: str) -> str:
    stripped = body.strip()
    heading = f"## {section}"
    if stripped.startswith("## "):
        return stripped
    if not stripped:
        return heading
    return f"{heading}\n{stripped}"


def _chunks_for_section(
    page: PdfPage,
    *,
    section: str,
    body: str,
    max_tokens: int,
    overlap_tokens: int,
    start_index: int,
) -> list[Chunk]:
    display = _section_display_text(section, body)
    enc = _encoding()
    tokens = enc.encode(display)
    if not tokens:
        return []

    if len(tokens) <= max_tokens:
        return [
            _make_chunk(
                page,
                section=section,
                text=display,
                token_count=len(tokens),
                index=start_index,
            )
        ]

    heading = f"## {section}\n"
    heading_tokens = enc.encode(heading)
    content = display[len(heading) :] if display.startswith(heading) else display
    if display.startswith(f"## {section}") and not display.startswith(heading):
        # Heading with no newline after it — still peel the first line.
        first_newline = display.find("\n")
        content = display[first_newline + 1 :] if first_newline >= 0 else ""
    content_tokens = enc.encode(content)
    budget = max(max_tokens - len(heading_tokens), 1)
    step = max(budget - overlap_tokens, 1)

    chunks: list[Chunk] = []
    start = 0
    index = start_index
    while start < len(content_tokens):
        window_size = min(budget, len(content_tokens) - start)
        text = heading.strip()
        while window_size >= 0:
            window_text = enc.decode(content_tokens[start : start + window_size]).strip()
            candidate = f"{heading}{window_text}".strip() if window_text else heading.strip()
            if count_tokens(candidate) <= max_tokens or window_size == 0:
                text = candidate
                break
            window_size -= 1
        if text:
            chunks.append(
                _make_chunk(
                    page,
                    section=section,
                    text=text,
                    token_count=count_tokens(text),
                    index=index,
                )
            )
            index += 1
        if start + budget >= len(content_tokens):
            break
        start += step
    return chunks


def _make_chunk(
    page: PdfPage,
    *,
    section: str,
    text: str,
    token_count: int,
    index: int,
) -> Chunk:
    return Chunk(
        chunk_id=make_chunk_id(page.doc_id, page.page, index),
        doc_id=page.doc_id,
        title=page.title,
        page=page.page,
        text=text,
        well_ids=page.well_ids,
        token_count=token_count,
        section=section,
    )
