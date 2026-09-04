# Layer A evaluation

Component-isolated checks for the WellGround graph: **router**, **SQL planner**, **SQL execution**, **RAG retrieval**, and **verifier**. End-to-end traces (Layer B) are out of scope here.

## Files

| Path | Role |
|---|---|
| [`golden.jsonl`](golden.jsonl) | Reviewed gold set used by CI |
| [`golden_candidates.jsonl`](golden_candidates.jsonl) | Bootstrap output (audit); extra keys like `proposed_rag_hits` are ignored by the loader |
| [`verifier_cases.jsonl`](verifier_cases.jsonl) | Synthetic verifier pass/fail pairs (no LLM, no indexes) |
| [`scripts/bootstrap_eval_gold.py`](../scripts/bootstrap_eval_gold.py) | Propose SQL values and RAG `doc_id`+`page` from `data/release/` |

## Gold schema

Each `golden.jsonl` line is a `GoldCase`:

| Field | Used by |
|---|---|
| `id`, `question` | all |
| `tags` | `router`, `sql_plan`, `sql_exec`, `rag` |
| `expected_route` | router |
| `expected_sql_metric`, `expected_sql_params` | sql_plan, sql_exec |
| `gold_sql_column`, `gold_sql_value`, `tolerance` | sql_exec |
| `rag_query` (optional; default `question`) | rag |
| `gold_doc_id`, `gold_page` | rag (pass = this pair appears in top-6) |
| `gold_well_ids`, `notes` | review / bootstrap hints |

RAG gold is **`doc_id` + `page`**, not `chunk_id`, so evals survive re-chunking until the underlying PDF pages change. Tie failures to [`data/release/MANIFEST.json`](../data/release/MANIFEST.json) if you just promoted indexes.

PDF ingestion writes layout-aware page markdown (`##` sections and tables) via `scripts/unstructured_data.py`, then `scripts/build_index.py` chunks by section. Rebuild `data/processed/` after parser/chunker changes. Layer A RAG tests in CI still load **pinned** [`data/release/`](../data/release/) indexes until you promote.

## Workflow

```bash
# 1. Propose candidates from the pinned release snapshot (no API key).
uv run python scripts/bootstrap_eval_gold.py

# 2. Review evals/golden_candidates.jsonl (routes, SQL values, RAG doc/page).
# 3. Copy approved rows into evals/golden.jsonl (GoldCase fields only).

uv run pytest tests/evals/test_verifier_eval.py tests/evals/test_sql_execution.py tests/evals/test_rag_retrieval.py
uv run pytest tests/evals -m live   # router + SQL planner; needs FIREWORKS_API_KEY
```

Review checklist for each candidate:

- **Route**: would a field engineer agree `sql` / `rag` / `both` / `action`?
- **SQL**: metric and params match the question; auto-computed value looks right in DuckDB
- **RAG**: proposed doc/page actually contains the fact (open the title in the candidates report)
- **Both**: SQL and RAG gold fields are both populated
- **Secrets**: never paste keys into `notes` or JSONL

## Tests

| File | Component | LLM? | Data |
|---|---|---|---|
| `tests/evals/test_verifier_eval.py` | citation verifier | no | `verifier_cases.jsonl` |
| `tests/evals/test_sql_execution.py` | `run_metric` | no | `data/release/forge.duckdb` |
| `tests/evals/test_rag_retrieval.py` | hybrid Hit@6 | no | `data/release/{chroma,bm25}` |
| `tests/evals/test_router_live.py` | `router_node` | yes | gold questions |
| `tests/evals/test_sql_planner_live.py` | `sql_worker_node` plan only | yes | gold questions; DuckDB stubbed |

Live tests skip when `FIREWORKS_API_KEY` is unset. Skip/fail messages never include the key or a settings dump.

One router case (`sql-58-32-role`) is `xfail` (non-strict) because the current router often labels 58-32 catalog lookups as `rag`. Remove the mark when that miss is fixed.

```bash
uv run pytest tests/ -m "not live"   # deterministic only
uv run pytest tests/                 # includes live tests if the key is set
```

v1 targets: 100% verifier and SQL-exec match on gold; RAG `doc_id`+`page` in top-6; router and SQL planner exact match on tagged cases.

## Secrets

- Keep `FIREWORKS_API_KEY` in gitignored `.env` locally and in **GitHub Actions Secrets** (not Variables) for CI.
- Use a **dedicated CI Fireworks key** with usage limits, separate from local `.env` and Railway production.
- Bootstrap and SQL/RAG evals do **not** need the key.
- Never commit `.env`, never log `get_settings()`, never put keys in golden JSONL or pytest output.
- The CI workflow does not run on **fork pull requests**, so the secret is not exposed to untrusted code.
- If a key leaks: revoke it in the Fireworks dashboard, mint a new one, update GitHub Secrets / `.env` / Railway api variables, re-run CI.
