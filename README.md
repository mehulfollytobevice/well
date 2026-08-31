# WellGround (ForgeOps Agent)

A production-shaped reference implementation of **grounded agentic ops Q&A** for enhanced geothermal systems (EGS).

Natural language → route to SQL and/or hybrid RAG → synthesize with citations → optional human-in-the-loop action → evaluated for route accuracy, faithfulness, and tool-use correctness.

> **Status:** Prototype phase. V1 of the RAG is ready. Next phase is Evaluation and UI development 

---

## Why this exists

Field and reservoir engineers work across two worlds at once:

- **Structured operational data** — well metadata, injection/production rates, temperatures, pressures, test events
- **Unstructured technical knowledge** — completion reports, stimulation summaries, logging interpretations, DOE/GDR publications

WellGround is a reference agent that answers ops questions by deciding *which* world to query (or both), grounding every answer in retrieved evidence, and optionally drafting an action that requires explicit human approval before it “executes.”

The goal is not a chatbot demo. It is a reusable pattern for:

- Tool routing and planner–worker orchestration
- Hybrid retrieval over documents + operational records
- Semantic grounding of domain concepts (wells, tests, metrics)
- Evaluation, tracing, and HITL checkpoints suitable for production iteration

Domain context is **Utah FORGE** (DOE’s public EGS research site) — the same problem class as commercial next-gen geothermal ops (horizontal wells, stimulation, circulation, temperature/pressure/flow).

---



## Example questions


| Question                                                                                                       | Expected route    |
| -------------------------------------------------------------------------------------------------------------- | ----------------- |
| “What’s the average production wellhead temperature for 16B during the Aug–Sep 2024 circulation test?”         | SQL               |
| “Summarize how 16A was stimulated and what peak flow was reported.”                                            | RAG               |
| “Compare injection vs production temps for 16A/16B last week of the test, and cite the test report procedure.” | SQL + RAG         |
| “Flag 16B for inspection if outlet temperature dropped more than 5% week-over-week.”                           | SQL → HITL action |


---



## Architecture

```
User question
      │
      ▼
┌───────────────┐
│ Planner/Router│  structured output: {route, rationale, subqueries}
└───────┬───────┘
        │
   ┌────┼────────────┐
   ▼    ▼            ▼
  SQL  Hybrid RAG   Action
 worker  worker     drafter
   │    │            │
   └────┤            ▼
        ▼      HITL gate ──► approve? ──► audit log
   Synthesizer
        │
        ▼
 Answer + citations + tool trace
```



### Nodes


| Node              | Responsibility                                                                                           |
| ----------------- | -------------------------------------------------------------------------------------------------------- |
| **Router**        | Classifies intent; emits structured route (`sql`                                                         |
| **SQL worker**    | Schema-aware queries over wells, time series, and test events; returns rows + the SQL used               |
| **RAG worker**    | Hybrid retrieval (vector + BM25) over chunked reports; returns passages with doc/page ids                |
| **Synthesizer**   | Merges evidence; refuses when grounding is weak; always attaches sources                                 |
| **Action + HITL** | Drafts a proposed ops action (e.g. flag well for review); pauses for approval; writes an audit log entry |




### Design principles

- **Evidence over eloquence** — no answer without citations or query traces
- **Tools over free-form SQL when possible** — curated metric/tools for common asks; constrained free SQL as an advanced path
- **Fail closed** — thin evidence → refuse or ask a clarifying question
- **Observable by default** — every run logs route, tools, latency, and approximate cost

---



## Data sources (public)

Scoped to **Utah FORGE** via the [Geothermal Data Repository (GDR)](https://gdr.openei.org/) and the [FORGE project data dashboard](https://utahforge.com/project-data-dashboard/).


| Layer                 | Content                                                                                                                           | Store                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| **Structured**        | Well metadata (16A, 16B, 58-32, …); circulation / injection–production time series (flow, WHP, temperature); test/event summaries | DuckDB (or SQLite)        |
| **Unstructured**      | Stimulation, production, and logging reports (PDFs); selected DOE/EGS technical papers                                            | Chroma or pgvector + BM25 |
| **Out of scope (v1)** | DAS / geophone data lakes, multimodal well-log vision                                                                             | Deferred                  |


Optional breadth later: SMU/NGDS nationwide heat-flow and borehole temperature catalogs on GDR.

---



## Tech stack


| Concern                   | Choice                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------- |
| Orchestration             | LangGraph (explicit graph: router → workers → synthesizer)                          |
| LLM                       | Anthropic Claude (tool use, structured outputs, streaming)                          |
| Structured data           | DuckDB + schema/prompt injection (hand-rolled tools + optional SQL)                 |
| Unstructured RAG          | Embeddings + hybrid search (vector + BM25)                                          |
| Semantic grounding (lite) | `metrics.yaml` / catalog mapping business concepts → SQL/tools                      |
| API                       | FastAPI (async)                                                                     |
| UI                        | Streamlit or lightweight React                                                      |
| Eval                      | Golden dataset + automated checks (route, faithfulness, tool-use)                   |
| Observability             | Structured JSON run logs; optional LangSmith                                        |
| Packaging                 | Docker; CI with tests                                                               |
| Stretch                   | MCP server exposing `query_wells` / `search_docs`; Azure Container Apps + Key Vault |


---



## Success metrics

The agent is “done” when these are measurable, not when the UI looks finished.


| Metric                   | Target (v1)                                                     |
| ------------------------ | --------------------------------------------------------------- |
| **Route accuracy**       | ≥ 90% on golden set (correct SQL / RAG / both / action)         |
| **Faithfulness**         | Answers supported by retrieved rows/passages; refusals when not |
| **Tool-use correctness** | Valid SQL/tool calls; no destructive queries; schema-respecting |
| **Citation coverage**    | Every factual claim tied to a source id (query id or doc/page)  |
| **HITL integrity**       | No action side effect without explicit approval                 |
| **Latency / cost**       | Logged per run; regressions caught in CI eval                   |


---



## Project layout (planned)

```
well/
├── README.md
├── LICENSE
├── data/                 # raw downloads + processed DuckDB / embeddings (gitignored bulky files)
├── docs/                 # architecture notes, data provenance
├── evals/                # golden questions, expected routes, graders
├── src/
│   ├── agent/            # LangGraph graph, nodes, state
│   ├── tools/            # SQL, RAG, action tools
│   ├── retrieval/        # chunking, hybrid search
│   ├── semantic/         # metrics catalog
│   ├── api/              # FastAPI app
│   └── observability/    # tracing, run logs
├── ui/                   # Streamlit / React
├── tests/
├── Dockerfile
└── pyproject.toml
```

---



## Roadmap

1. **Data bootstrap** — download FORGE CSVs/PDFs; load DuckDB schema; ingest and index documents
2. **Tools** — `run_sql` / curated metric tools + hybrid `search_docs`
3. **Graph** — LangGraph router → SQL/RAG → synthesizer
4. **HITL** — draft “flag well” action + approval gate + audit log
5. **Evals** — 25–40 golden questions; CI-friendly regression harness
6. **Serve** — FastAPI + simple UI + Docker
7. **Polish** — MCP tool surface; optional Azure deploy

---



## Local development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY=...
uv sync                # creates .venv and installs deps (+ editable package)
uv run wellground version
uv run pytest
# later:
# uv run wellground serve
```

---



## Disclaimer

This project uses **public** Utah FORGE / DOE GDR datasets for educational and portfolio purposes. It is not affiliated with Fervo Energy, DOE, or the Utah FORGE project. It is not a substitute for engineering judgment or operational systems.

---



## License

[MIT](./LICENSE)