FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data/release ./data/release

RUN uv sync --frozen --no-dev

ENV HF_HOME=/app/.cache/huggingface
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

ENV WELLGROUND_ENV=production
ENV WELLGROUND_DUCKDB_PATH=/app/data/release/forge.duckdb
ENV WELLGROUND_CHROMA_PATH=/app/data/release/chroma
ENV WELLGROUND_BM25_PATH=/app/data/release/bm25

EXPOSE 8000
CMD ["sh", "-c", "uv run uvicorn wellground.api.app:app --host :: --port ${PORT:-8000}"]
