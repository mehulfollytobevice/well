"""Dense vector retrieval with Chroma and BGE embeddings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from wellground.retrieval.bm25_index import SearchHit, chunk_index_text
from wellground.retrieval.chunker import Chunk, load_chunks_jsonl

DEFAULT_CHROMA_DIR = Path("data/processed/chroma")
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
COLLECTION_NAME = "forge_chunks"


@lru_cache
def _embedding_model(model_name: str = DEFAULT_MODEL) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def _chunk_metadata(chunk: Chunk) -> dict[str, str | int]:
    return {
        "doc_id": chunk.doc_id,
        "title": chunk.title,
        "page": chunk.page,
        "text": chunk.text,
        "well_ids": ",".join(chunk.well_ids),
        "token_count": chunk.token_count,
        "section": chunk.section,
    }


def _chunk_from_metadata(chunk_id: str, metadata: dict[str, Any]) -> Chunk:
    return Chunk.from_mapping(
        {
            "chunk_id": chunk_id,
            "doc_id": metadata["doc_id"],
            "title": metadata["title"],
            "page": metadata["page"],
            "text": metadata["text"],
            "well_ids": metadata.get("well_ids", ""),
            "token_count": metadata.get("token_count") or 0,
            "section": metadata.get("section") or "",
        }
    )


class DenseIndex:
    """Chroma-backed dense index over chunked PDF passages."""

    def __init__(
        self,
        *,
        persist_dir: Path,
        model_name: str = DEFAULT_MODEL,
        collection: Collection | None = None,
    ) -> None:
        self.persist_dir = persist_dir
        self.model_name = model_name
        self._model = _embedding_model(model_name)
        if collection is None:
            client = chromadb.PersistentClient(path=str(persist_dir))
            collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        self._collection = collection

    @property
    def chunk_count(self) -> int:
        return int(self._collection.count())

    def _encode_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 32,
        )
        return vectors.tolist()

    def _encode_query(self, query: str) -> list[float]:
        vector = self._model.encode(
            query,
            normalize_embeddings=True,
            prompt_name="query",
        )
        return vector.tolist()

    def build(self, chunks: list[Chunk]) -> DenseIndex:
        """Embed chunks and persist them in Chroma."""
        if not chunks:
            raise ValueError("DenseIndex requires at least one chunk")

        client = chromadb.PersistentClient(path=str(self.persist_dir))
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        texts = [chunk_index_text(chunk) for chunk in chunks]
        embeddings = self._encode_documents(texts)

        batch_size = 64
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            collection.add(
                ids=[chunk.chunk_id for chunk in batch],
                embeddings=embeddings[start : start + len(batch)],
                documents=[chunk.text for chunk in batch],
                metadatas=[_chunk_metadata(chunk) for chunk in batch],
            )

        self._collection = collection
        return self

    def search(self, query: str, *, top_k: int = 6) -> list[SearchHit]:
        """Return the top-k chunks ranked by cosine similarity."""
        if top_k <= 0 or self.chunk_count == 0:
            return []

        query_embedding = self._encode_query(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.chunk_count),
            include=["metadatas", "distances"],
        )

        hits: list[SearchHit] = []
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        for rank, (chunk_id, metadata, distance) in enumerate(
            zip(ids, metadatas, distances, strict=True),
            start=1,
        ):
            # Chroma cosine distance is 1 - similarity for normalized vectors.
            score = 1.0 - float(distance)
            hits.append(
                SearchHit(
                    chunk=_chunk_from_metadata(chunk_id, metadata),
                    score=score,
                    rank=rank,
                )
            )
        return hits

    @classmethod
    def load(
        cls,
        persist_dir: Path,
        *,
        model_name: str = DEFAULT_MODEL,
    ) -> DenseIndex:
        """Open a persisted Chroma index."""
        if not persist_dir.is_dir():
            raise FileNotFoundError(f"Dense index not found: {persist_dir}")

        client = chromadb.PersistentClient(path=str(persist_dir))
        collection = client.get_collection(name=COLLECTION_NAME)
        if collection.count() == 0:
            raise FileNotFoundError(f"Dense index at {persist_dir} is empty")

        return cls(persist_dir=persist_dir, model_name=model_name, collection=collection)

    @classmethod
    def build_from_chunks(
        cls,
        chunks: list[Chunk],
        *,
        persist_dir: Path = DEFAULT_CHROMA_DIR,
        model_name: str = DEFAULT_MODEL,
    ) -> DenseIndex:
        """Create and persist a dense index from an in-memory chunk list."""
        index = cls(persist_dir=persist_dir, model_name=model_name)
        return index.build(chunks)

    @classmethod
    def load_chunks_from_index_dir(cls, chunks_path: Path) -> list[Chunk]:
        """Load chunk records saved alongside other indexes."""
        return load_chunks_jsonl(chunks_path)
