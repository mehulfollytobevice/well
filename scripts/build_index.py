#!/usr/bin/env python3
"""Build retrieval indexes from parsed PDF pages (BM25 + dense Chroma)."""

from __future__ import annotations

import argparse
from pathlib import Path

from wellground.retrieval.bm25_index import BM25Index, DEFAULT_INDEX_DIR
from wellground.retrieval.chunker import (
    chunk_pages,
    load_chunks_jsonl,
    load_pages_jsonl,
    write_chunks_jsonl,
)
from wellground.retrieval.dense_index import DEFAULT_CHROMA_DIR, DenseIndex
from wellground.retrieval.hybrid import HybridRetriever

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGES = PROJECT_ROOT / "data/processed/pdf_pages.jsonl"
DEFAULT_CHUNKS = PROJECT_ROOT / "data/processed/chunks.jsonl"
DEFAULT_BM25_DIR = PROJECT_ROOT / DEFAULT_INDEX_DIR
DEFAULT_CHROMA_PATH = PROJECT_ROOT / DEFAULT_CHROMA_DIR


def _print_hits(label: str, hits: list, top_k: int) -> None:
    print(f"\n{label}")
    if not hits:
        print("  (no hits)")
        return
    for hit in hits[:top_k]:
        preview = hit.chunk.text.replace("\n", " ")[:120]
        print(
            f"  #{hit.rank} score={hit.score:.3f} "
            f"{hit.chunk.chunk_id} — {preview!r}..."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        type=Path,
        default=DEFAULT_PAGES,
        help="Parsed page JSONL from scripts/unstructured_data.py",
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS,
        help="Where to write/read chunk JSONL (default: data/processed/chunks.jsonl)",
    )
    parser.add_argument(
        "--bm25-dir",
        type=Path,
        default=DEFAULT_BM25_DIR,
        help="Directory for the BM25 index (default: data/processed/bm25/)",
    )
    parser.add_argument(
        "--chroma-dir",
        type=Path,
        default=DEFAULT_CHROMA_PATH,
        help="Directory for the Chroma index (default: data/processed/chroma/)",
    )
    parser.add_argument(
        "--reuse-chunks",
        action="store_true",
        help="Skip chunking and load existing --chunks file",
    )
    parser.add_argument(
        "--skip-bm25",
        action="store_true",
        help="Skip building the BM25 index",
    )
    parser.add_argument(
        "--skip-dense",
        action="store_true",
        help="Skip building the dense Chroma index",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Optional smoke-test query after building indexes",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=6,
        help="Top-k for --query smoke test (default: 6)",
    )
    args = parser.parse_args()

    if args.reuse_chunks:
        if not args.chunks.is_file():
            raise SystemExit(f"Chunks file not found: {args.chunks}")
        chunks = load_chunks_jsonl(args.chunks)
        print(f"Loaded {len(chunks)} chunks from {args.chunks}")
    else:
        if not args.pages.is_file():
            raise SystemExit(
                f"Pages file not found: {args.pages}\n"
                "Run scripts/unstructured_data.py first, or pass --reuse-chunks."
            )
        pages = load_pages_jsonl(args.pages)
        chunks = chunk_pages(pages)
        write_chunks_jsonl(chunks, args.chunks)
        print(f"Chunked {len(pages)} pages -> {len(chunks)} chunks")
        print(f"Wrote {args.chunks}")

    if not args.skip_bm25:
        bm25 = BM25Index.build(chunks)
        bm25.save(args.bm25_dir)
        print(f"Built BM25 index over {len(chunks)} chunks -> {args.bm25_dir}")
    else:
        bm25 = None

    if not args.skip_dense:
        dense = DenseIndex.build_from_chunks(chunks, persist_dir=args.chroma_dir)
        print(
            f"Built dense index over {dense.chunk_count} chunks -> {args.chroma_dir}"
        )
    else:
        dense = None

    if args.query:
        if bm25 is None:
            bm25 = BM25Index.load(args.bm25_dir)
        if dense is None:
            dense = DenseIndex.load(args.chroma_dir)

        print(f"\nQuery: {args.query!r}")
        _print_hits("BM25", bm25.search(args.query, top_k=args.top_k), args.top_k)
        _print_hits("Dense", dense.search(args.query, top_k=args.top_k), args.top_k)

        hybrid = HybridRetriever(bm25, dense)
        hybrid_hits = hybrid.search(args.query, top_k=args.top_k)
        print("\nHybrid (RRF)")
        if not hybrid_hits:
            print("  (no hits)")
        for hit in hybrid_hits:
            preview = hit.chunk.text.replace("\n", " ")[:120]
            print(
                f"  #{hit.rank} score={hit.score:.4f} "
                f"bm25={hit.bm25_rank} dense={hit.dense_rank} "
                f"{hit.chunk_id} — {preview!r}..."
            )


if __name__ == "__main__":
    main()
