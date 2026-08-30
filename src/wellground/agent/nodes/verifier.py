"""Deterministic citation checks on a synthesizer response."""

from __future__ import annotations

import json
import re

from wellground.agent.schemas import AgentResponse, Evidence, RagEvidence, SqlEvidence

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "during",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)


def verify_response(
    response: AgentResponse,
    evidence: list[Evidence] | None = None,
) -> tuple[bool, str]:
    """Return (passed, notes). Notes list failures; empty string on success."""
    catalog = evidence if evidence is not None else response.evidence
    by_id = {item.evidence_id: item for item in catalog if item.evidence_id}

    if response.status == "answered":
        if not catalog:
            return False, "No evidence retrieved; cannot answer."
        if not response.claims:
            return False, "Answered status requires at least one claim."

    if response.status in {"refused", "needs_clarification"}:
        return True, ""

    problems: list[str] = []
    for i, claim in enumerate(response.claims):
        if not claim.source_ids:
            problems.append(f"claim[{i}] has no source_ids")
            continue
        missing = [sid for sid in claim.source_ids if sid not in by_id]
        if missing:
            problems.append(f"claim[{i}] cites unknown ids: {missing}")
            continue
        cited_text = " ".join(_evidence_text(by_id[sid]) for sid in claim.source_ids)
        if not _shares_content_token(claim.text, cited_text):
            problems.append(f"claim[{i}] is not grounded in cited evidence")

    if problems:
        return False, "; ".join(problems)
    return True, ""


def _evidence_text(item: Evidence) -> str:
    if isinstance(item, RagEvidence):
        return f"{item.title} {item.excerpt}"
    if isinstance(item, SqlEvidence):
        return f"{item.sql} {json.dumps(item.rows, default=str)}"
    return ""


def _shares_content_token(claim: str, evidence: str) -> bool:
    claim_tokens = _tokens(claim) - STOPWORDS
    evidence_tokens = _tokens(evidence) - STOPWORDS
    if not claim_tokens:
        return False
    return bool(claim_tokens & evidence_tokens)


def _tokens(text: str) -> set[str]:
    parts = re.findall(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*", text.lower())
    return set(parts)
