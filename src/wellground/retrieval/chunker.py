"""Split parsed PDF pages into retrieval-sized chunks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

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


@lru_cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return the cl100k_base token count for a string."""
    return len(_encoding().encode(text))


def make_chunk_id(doc_id: str, page: int, index: int) -> str:
    """Stable id for citations, e.g. daily_reports/report#p001#c00."""
    return f"{doc_id}#p{page:03d}#c{index:02d}"


def chunk_page(
    page: PdfPage,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split one page into overlapping token windows."""
    enc = _encoding()
    tokens = enc.encode(page.text)

    if not tokens:
        return []

    if len(tokens) <= max_tokens:
        return [
            Chunk(
                chunk_id=make_chunk_id(page.doc_id, page.page, 0),
                doc_id=page.doc_id,
                title=page.title,
                page=page.page,
                text=page.text,
                well_ids=page.well_ids,
                token_count=len(tokens),
            )
        ]

    chunks: list[Chunk] = []
    start = 0
    index = 0
    step = max(max_tokens - overlap_tokens, 1)

    while start < len(tokens):
        window = tokens[start : start + max_tokens]
        text = enc.decode(window).strip()
        if text:
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(page.doc_id, page.page, index),
                    doc_id=page.doc_id,
                    title=page.title,
                    page=page.page,
                    text=text,
                    well_ids=page.well_ids,
                    token_count=len(window),
                )
            )
            index += 1
        if start + max_tokens >= len(tokens):
            break
        start += step

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
            chunks.append(Chunk(**row))
    return chunks
