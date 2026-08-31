# Production deploy snapshot (`data/release/`)

This folder is the **pinned production corpus** baked into the Railway API Docker image. It is a derived work of public Utah FORGE / DOE Geothermal Data Repository (GDR) datasets.

Local experiments use gitignored `data/processed/`. Run `uv run python scripts/promote_indexes.py` after rebuilding indexes to refresh this snapshot.

## Artifacts

| Path | Role |
|---|---|
| `forge.duckdb` | Structured wells + circulation time series |
| `chroma/` | Dense vector index (BGE embeddings) |
| `bm25/` | Sparse BM25 index + chunk metadata |
| `MANIFEST.json` | Promotion timestamp and source DOIs |

## License

Upstream GDR datasets are licensed under **Creative Commons Attribution 4.0 (CC-BY 4.0)** unless noted otherwise. WellGround retrieval indexes are derived from those sources. **Attribution is required** when redistributing or deploying this snapshot.

## Source datasets

| Content | DOI |
|---|---|
| Extended circulation time series (Aug–Sep 2024) | [10.15121/2475065](https://doi.org/10.15121/2475065) |
| Circulation daily reports | [10.15121/2455019](https://doi.org/10.15121/2455019) |
| Injection / production test reports | [10.15121/2473673](https://doi.org/10.15121/2473673) |
| Well GPS metadata | [10.15121/1838418](https://doi.org/10.15121/1838418) |

Full acquisition notes: [`../PROVENANCE.md`](../PROVENANCE.md).

## Recommended citations

McLennan, J., England, K., & Swearingen, L. (2024). *Utah FORGE: Wells 16A(78)-32 and 16B(78)-32 Extended Circulation Test Data — August and September 2024*. Geothermal Data Repository. https://doi.org/10.15121/2475065

Swearingen, L. (2024). *Utah FORGE: Wells 16A(78)-32 and 16B(78)-32 Circulation Test Daily Reports from August 2024*. Geothermal Data Repository. https://doi.org/10.15121/2455019

Kolomytsev, L., & Chadwick, C. (2024). *Utah FORGE: Injection and Production Test results and Reports from August 2024*. Geothermal Data Repository. https://doi.org/10.15121/2473673

## Disclaimer

Public Utah FORGE / DOE GDR data for research and portfolio use. Not affiliated with DOE, University of Utah, or Utah FORGE operators. Not a substitute for engineering judgment or operational systems.
