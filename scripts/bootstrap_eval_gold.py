#!/usr/bin/env python3
"""Propose Layer A gold cases from README seeds + the data/release snapshot.

Does not call Fireworks. SQL values come from DuckDB; RAG doc/page from hybrid
search with a keyword fallback over chunks.jsonl.

Review evals/golden_candidates.jsonl, then copy approved rows to evals/golden.jsonl.
Never print environment variables or API keys.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wellground.evals.loader import evals_dir, repo_root
from wellground.evals.schema import ComponentTag, GoldCase, RouteName
from wellground.retrieval.hybrid import HybridRetriever
from wellground.tools.rag import search_docs
from wellground.tools.sql import run_metric

RELEASE = repo_root() / "data" / "release"
METRIC_COLUMN = {
    "well_role": "role",
    "well_count": "well_count",
    "list_wells": "well_id",
    "avg_temperature": "avg_temperature",
    "avg_pressure": "avg_pressure",
    "avg_flow_rate": "avg_flow_rate",
    "timeseries_peak": "peak_value",
}


@dataclass
class Seed:
    id: str
    question: str
    expected_route: RouteName
    tags: list[ComponentTag]
    expected_sql_metric: str | None = None
    expected_sql_params: dict[str, str] = field(default_factory=dict)
    rag_query: str | None = None
    rag_keywords: list[str] = field(default_factory=list)
    gold_well_ids: list[str] = field(default_factory=list)
    notes: str = ""


def _seeds() -> list[Seed]:
    """README examples + catalog coverage + report-grounded RAG/both/action."""
    return [
        Seed(
            id="sql-16b-avg-wh-temp",
            question=(
                "What's the average production wellhead temperature for 16B "
                "during the Aug–Sep 2024 circulation test?"
            ),
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="avg_temperature",
            expected_sql_params={"well_id": "16B"},
            gold_well_ids=["16B"],
            notes="README SQL example",
        ),
        Seed(
            id="sql-16a-role",
            question="Which well is the injector, 16A or 16B? What is 16A's role?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="well_role",
            expected_sql_params={"well_id": "16A"},
            gold_well_ids=["16A"],
        ),
        Seed(
            id="sql-16b-role",
            question="What is the operational role of well 16B?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="well_role",
            expected_sql_params={"well_id": "16B"},
            gold_well_ids=["16B"],
        ),
        Seed(
            id="sql-58-32-role",
            question="What is the role of well 58-32 in the FORGE catalog?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="well_role",
            expected_sql_params={"well_id": "58-32"},
            gold_well_ids=["58-32"],
        ),
        Seed(
            id="sql-well-count",
            question="How many wells are in the Utah FORGE catalog?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="well_count",
        ),
        Seed(
            id="sql-list-wells-first",
            question="List the wells in the FORGE catalog.",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="list_wells",
            notes="Gold value is first well_id after ORDER BY well_id",
        ),
        Seed(
            id="sql-16a-avg-pressure",
            question=(
                "What was the average wellhead pressure on 16A during the "
                "August–September 2024 circulation test?"
            ),
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="avg_pressure",
            expected_sql_params={"well_id": "16A"},
            gold_well_ids=["16A"],
        ),
        Seed(
            id="sql-16b-avg-pressure",
            question="Average wellhead pressure for production well 16B over the circulation test.",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="avg_pressure",
            expected_sql_params={"well_id": "16B"},
            gold_well_ids=["16B"],
        ),
        Seed(
            id="sql-16b-avg-flow",
            question="What was the average flow rate for 16B during the 2024 circulation test?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="avg_flow_rate",
            expected_sql_params={"well_id": "16B"},
            gold_well_ids=["16B"],
        ),
        Seed(
            id="sql-16b-peak-temp",
            question="What was the peak wellhead temperature on 16B during the circulation test?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="timeseries_peak",
            expected_sql_params={"well_id": "16B", "column": "temperature", "agg": "MAX"},
            gold_well_ids=["16B"],
        ),
        Seed(
            id="sql-16b-peak-pressure",
            question=(
                "What was the maximum wellhead pressure recorded on 16B "
                "during the circulation test?"
            ),
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="timeseries_peak",
            expected_sql_params={"well_id": "16B", "column": "pressure", "agg": "MAX"},
            gold_well_ids=["16B"],
        ),
        Seed(
            id="sql-16a-peak-pressure",
            question="Peak wellhead pressure for injection well 16A in Aug–Sep 2024.",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="timeseries_peak",
            expected_sql_params={"well_id": "16A", "column": "pressure", "agg": "MAX"},
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16a-plt-log",
            question="Summarize the PLT logging operations on 16A during the circulation test.",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A PLT log circulation test SLB",
            rag_keywords=["PLT", "16A"],
            gold_well_ids=["16A"],
            notes="README-style qualitative ops; PLT appears in daily reports",
        ),
        Seed(
            id="rag-16a-ev-camera",
            question="When was the EV camera run in 16A and what did operations report?",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A EV camera circulation test",
            rag_keywords=["EV camera", "16A"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16a-step7-10bpm",
            question="What pump rate was used for Step 7 of the 16A circulation test?",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A Step 7 circulation test 10.0 bpm",
            rag_keywords=["Step 7", "10.0 bpm"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16a-tracers",
            question="Who was adding tracers and sampling during the 16A circulation test?",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A RESMAN QuantumPro tracers sampling",
            rag_keywords=["RESMAN", "QuantumPro"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16a-injection-profile",
            question="Summarize the SLB injection profile findings for well 16A.",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A SLB injection profile final report",
            rag_keywords=["Injection Profile"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16b-production-log",
            question="What does the SLB production log report say about well 16B?",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16B SLB production log final report",
            rag_keywords=["Production Log", "16B"],
            gold_well_ids=["16B"],
        ),
        Seed(
            id="rag-16b-cleanout",
            question="Summarize the 16B clean out operations before the circulation test.",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16B clean out report July 2024",
            rag_keywords=["Clean Out", "16B"],
            gold_well_ids=["16B"],
        ),
        Seed(
            id="rag-16a-liberty-rigup",
            question="What equipment did Liberty stage on the pad for the 16A circulation test?",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A Liberty pumping equipment rigging up",
            rag_keywords=["Liberty", "pumping equipment"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16a-lightning-shutdown",
            question="Why did 16A circulation-test operations shut down for Wagstaff policy?",
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16A Wagstaff lightning strikes shutdown PLT",
            rag_keywords=["lightening", "Wagstaff"],
            gold_well_ids=["16A"],
            notes="PDF OCR uses 'lightening'",
        ),
        Seed(
            id="both-16b-temp-and-step7",
            question=(
                "What was 16B average wellhead temperature during the circulation test, "
                "and cite the daily report for Step 7 pump rate on 16A?"
            ),
            expected_route="both",
            tags=["router", "sql_plan", "sql_exec", "rag"],
            expected_sql_metric="avg_temperature",
            expected_sql_params={"well_id": "16B"},
            rag_query="16A Step 7 circulation test 10.0 bpm",
            rag_keywords=["Step 7", "10.0 bpm"],
            gold_well_ids=["16B", "16A"],
            notes="README both-style: numbers + report procedure",
        ),
        Seed(
            id="both-16a-pressure-injection-profile",
            question=(
                "Give the average 16A wellhead pressure for the Aug–Sep 2024 circulation test "
                "and cite the SLB injection profile report."
            ),
            expected_route="both",
            tags=["router", "sql_plan", "sql_exec", "rag"],
            expected_sql_metric="avg_pressure",
            expected_sql_params={"well_id": "16A"},
            rag_query="16A SLB injection profile final report",
            rag_keywords=["Injection Profile"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="both-16b-flow-production-log",
            question=(
                "What was the average flow rate on 16B during the circulation test, "
                "and cite the SLB production log report for 16B?"
            ),
            expected_route="both",
            tags=["router", "sql_plan", "sql_exec", "rag"],
            expected_sql_metric="avg_flow_rate",
            expected_sql_params={"well_id": "16B"},
            rag_query="16B SLB production log final report",
            rag_keywords=["Production Log"],
            gold_well_ids=["16B"],
        ),
        Seed(
            id="action-flag-16b",
            question=(
                "Flag 16B for inspection if outlet temperature dropped more than 5% week-over-week."
            ),
            expected_route="action",
            tags=["router"],
            gold_well_ids=["16B"],
            notes="README HITL example",
        ),
        Seed(
            id="action-flag-16a-review",
            question="Flag well 16A for review after the circulation test.",
            expected_route="action",
            tags=["router"],
            gold_well_ids=["16A"],
        ),
        Seed(
            id="rag-16b-daily-rpt1",
            question=(
                "What were current operations on the 16B circulation test daily report "
                "for 7 August 2024?"
            ),
            expected_route="rag",
            tags=["router", "rag"],
            rag_query="16B Circulation Test RPT1 8-7-2024 current operations",
            rag_keywords=["16B(78)-32 Circulation Test RPT1"],
            gold_well_ids=["16B"],
        ),
        Seed(
            id="sql-56-32-role",
            question="Is 56-32 a production well or a monitoring well?",
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="well_role",
            expected_sql_params={"well_id": "56-32"},
            gold_well_ids=["56-32"],
        ),
        Seed(
            id="sql-16b-min-temp",
            question=(
                "What was the minimum wellhead temperature on 16B during the circulation test?"
            ),
            expected_route="sql",
            tags=["router", "sql_plan", "sql_exec"],
            expected_sql_metric="timeseries_peak",
            expected_sql_params={"well_id": "16B", "column": "temperature", "agg": "MIN"},
            gold_well_ids=["16B"],
        ),
        Seed(
            id="both-16b-peak-temp-plt-context",
            question=(
                "What was peak 16B wellhead temperature in the circulation test, "
                "and cite the 16A PLT logging daily report?"
            ),
            expected_route="both",
            tags=["router", "sql_plan", "sql_exec", "rag"],
            expected_sql_metric="timeseries_peak",
            expected_sql_params={"well_id": "16B", "column": "temperature", "agg": "MAX"},
            rag_query="16A PLT log circulation test SLB",
            rag_keywords=["PLT"],
            gold_well_ids=["16B", "16A"],
        ),
    ]


@dataclass
class ChunkRec:
    doc_id: str
    page: int
    text: str
    well_ids: list[str]
    title: str


def _load_chunks(path: Path) -> list[ChunkRec]:
    rows: list[ChunkRec] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rows.append(
            ChunkRec(
                doc_id=rec["doc_id"],
                page=int(rec["page"]),
                text=rec["text"],
                well_ids=list(rec.get("well_ids") or []),
                title=rec.get("title") or rec["doc_id"],
            )
        )
    return rows


def _keyword_propose(seed: Seed, chunks: Sequence[ChunkRec]) -> tuple[str, int] | None:
    if not seed.rag_keywords:
        return None
    needles = [k.lower() for k in seed.rag_keywords]
    best: tuple[int, str, int] | None = None
    for chunk in chunks:
        text = chunk.text.lower()
        title = chunk.title.lower()
        hay = f"{title} {text}"
        score = sum(1 for needle in needles if needle in hay)
        if score == 0:
            continue
        if seed.gold_well_ids:
            score += len(set(seed.gold_well_ids) & set(chunk.well_ids))
            title_l = chunk.title.lower()
            if any(well.lower() in title_l for well in seed.gold_well_ids):
                score += 2
        if best is None or score > best[0]:
            best = (score, chunk.doc_id, chunk.page)
    if best is None:
        return None
    return best[1], best[2]


def _rank1_has_keywords(
    seed: Seed,
    doc_id: str | None,
    page: int | None,
    chunks: Sequence[ChunkRec],
) -> bool:
    if not doc_id or page is None or not seed.rag_keywords:
        return bool(doc_id)
    needles = [k.lower() for k in seed.rag_keywords]
    for chunk in chunks:
        if chunk.doc_id == doc_id and chunk.page == page:
            hay = f"{chunk.title} {chunk.text}".lower()
            return any(needle in hay for needle in needles)
    return False


def _fill_sql(seed: Seed, db_path: Path) -> tuple[str | None, float | int | str | None]:
    if not seed.expected_sql_metric:
        return None, None
    evidence = run_metric(seed.expected_sql_metric, seed.expected_sql_params, db_path=db_path)
    column = METRIC_COLUMN.get(seed.expected_sql_metric)
    if not column or not evidence.rows:
        return column, None
    value = evidence.rows[0].get(column)
    if isinstance(value, float):
        return column, value
    if isinstance(value, int) and not isinstance(value, bool):
        return column, value
    if value is None:
        return column, None
    return column, str(value)


def _top_hits(
    query: str, retriever: HybridRetriever, *, top_k: int = 3
) -> list[dict[str, Any]]:
    hits = search_docs(query, top_k=top_k, retriever=retriever)
    return [
        {"rank": i, "doc_id": hit.doc_id, "page": hit.page, "score": hit.score, "title": hit.title}
        for i, hit in enumerate(hits, start=1)
    ]


def bootstrap(out_path: Path) -> list[dict[str, Any]]:
    db_path = RELEASE / "forge.duckdb"
    bm25_dir = RELEASE / "bm25"
    chroma_dir = RELEASE / "chroma"
    chunks_path = bm25_dir / "chunks.jsonl"
    if not db_path.is_file():
        raise FileNotFoundError(f"Missing {db_path}")
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Missing {chunks_path}")

    print("Loading release hybrid index (local embeddings, no API key)...")
    retriever = HybridRetriever.load(bm25_dir=bm25_dir, chroma_dir=chroma_dir)
    chunks = _load_chunks(chunks_path)

    records: list[dict[str, Any]] = []
    for seed in _seeds():
        column, sql_value = _fill_sql(seed, db_path)
        rag_query = seed.rag_query or seed.question
        top = _top_hits(rag_query, retriever) if "rag" in seed.tags else []
        gold_doc: str | None = None
        gold_page: int | None = None
        proposal_source = ""
        if "rag" in seed.tags:
            if top:
                gold_doc = str(top[0]["doc_id"])
                gold_page = int(top[0]["page"])
                proposal_source = "hybrid_rank1"
            if not _rank1_has_keywords(seed, gold_doc, gold_page, chunks):
                fallback = _keyword_propose(seed, chunks)
                if fallback is not None:
                    gold_doc, gold_page = fallback
                    proposal_source = "keyword_scan" if not top else "keyword_over_rank1"

        payload: dict[str, Any] = {
            "id": seed.id,
            "question": seed.question,
            "tags": seed.tags,
            "expected_route": seed.expected_route,
            "expected_sql_metric": seed.expected_sql_metric,
            "expected_sql_params": seed.expected_sql_params,
            "gold_sql_column": column,
            "gold_sql_value": sql_value,
            "tolerance": 1.0,
            "rag_query": seed.rag_query,
            "gold_doc_id": gold_doc,
            "gold_page": gold_page,
            "gold_well_ids": seed.gold_well_ids,
            "notes": seed.notes,
            "proposed_rag_hits": top,
            "proposal_source": proposal_source,
        }
        records.append(payload)

        sql_disp = sql_value if sql_value is not None else "-"
        rag_disp = f"{(gold_doc or '-')[-48:]} p={gold_page}"
        print(f"{seed.id:42} {seed.expected_route:6} sql={sql_disp!s:.40} rag={rag_disp}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, default=str) + "\n")
    print(f"\nWrote {len(records)} candidates to {out_path}")
    _print_markdown(records)
    return records


def _print_markdown(records: list[dict[str, Any]]) -> None:
    print("\n## Review table\n")
    print("| id | route | sql | rag gold | top-1 |")
    print("|---|---|---|---|---|")
    for rec in records:
        sql = rec.get("gold_sql_value")
        rag = rec.get("gold_doc_id") or ""
        rag_short = rag[-56:] if rag else "-"
        top = rec.get("proposed_rag_hits") or []
        top1 = ""
        if top:
            top1 = f"{str(top[0]['doc_id'])[-40:]} p={top[0]['page']}"
        print(
            f"| {rec['id']} | {rec['expected_route']} | {sql} | "
            f"{rag_short} p={rec.get('gold_page')} | {top1} |"
        )


def _validate_as_gold(records: list[dict[str, Any]]) -> None:
    """Ensure reviewed-shaped records would parse as GoldCase (drops extra keys)."""
    errors = 0
    for rec in records:
        try:
            GoldCase.model_validate(rec)
        except Exception as exc:  # noqa: BLE001 — report all seed issues
            errors += 1
            print(f"INVALID {rec.get('id')}: {exc}")
    if errors:
        raise SystemExit(f"{errors} candidate(s) would not validate as GoldCase")
    print("All candidates validate as GoldCase.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=evals_dir() / "golden_candidates.jsonl",
        help="Candidate JSONL path (not the reviewed golden set)",
    )
    args = parser.parse_args()
    records = bootstrap(args.out)
    _validate_as_gold(records)


if __name__ == "__main__":
    main()
