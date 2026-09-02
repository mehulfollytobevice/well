"use client";

import { useState } from "react";
import type { AgentResponse } from "@/lib/types";
import { formatLatency } from "@/lib/format";
import { EvidenceCard } from "@/components/EvidenceCard";

function sourceRefLabel(sourceId: string, evidenceIndex: Map<string, number>): string {
  const index = evidenceIndex.get(sourceId);
  return index !== undefined ? `Source ${index + 1}` : sourceId;
}

export function AskPanel() {
  const [question, setQuestion] = useState(
    "Summarize how 16A was stimulated and what peak flow was reported.",
  );
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);
    const started = performance.now();
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? "Request failed");
      }
      setResponse(data);
      setLatencyMs(Math.round(performance.now() - started));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const evidenceIndex = new Map(
    response?.evidence.map((item, index) => [item.evidence_id, index]) ?? [],
  );

  return (
    <section className="panel">
      <form onSubmit={onSubmit} className="ask-form">
        <label htmlFor="question" className="form-label">Question</label>
        <textarea
          id="question"
          className="ask-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about wells, stimulation, flow rates…"
        />
        <button
          type="submit"
          className={`ask-button${loading ? " ask-button--loading" : ""}`}
          disabled={loading || question.trim().length === 0}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span className="ask-button__spinner" aria-hidden="true" />
              Thinking
              <span className="ask-button__dots" aria-hidden="true">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            </>
          ) : (
            "Ask WellGround"
          )}
        </button>
      </form>

      {error && <p className="error-banner">{error}</p>}

      {response && (
        <div className="response">
          <div className="meta">
            <span className="pill pill--status">{response.status}</span>
            <span className="pill pill--route">{response.route}</span>
            {latencyMs !== null && (
              <span className="pill pill--time">{formatLatency(latencyMs)}</span>
            )}
          </div>

          {response.refusal_reason && (
            <p className="error-banner">{response.refusal_reason}</p>
          )}

          {response.claims.length > 0 && (
            <section className="answer-card" aria-label="Answer">
              <h2 className="answer-card__heading">Answer</h2>
              <div className="answer-card__body">
                {response.claims.map((claim, index) => (
                  <p key={index} className="claim">
                    {claim.text}
                    {claim.source_ids.length > 0 && (
                      <span className="claim-sources">
                        {claim.source_ids.map((id) => sourceRefLabel(id, evidenceIndex)).join(", ")}
                      </span>
                    )}
                  </p>
                ))}
              </div>
            </section>
          )}

          {response.evidence.length > 0 && (
            <section className="evidence-section" aria-label="Evidence">
              <h2 className="evidence-section__heading">
                Supporting evidence
                <span className="evidence-section__count">{response.evidence.length}</span>
              </h2>
              <div className="evidence-list">
                {response.evidence.map((item, evidenceIndex) => (
                  <EvidenceCard
                    key={
                      item.evidence_id ||
                      (item.kind === "rag" ? item.chunk_id : item.query_id) ||
                      String(evidenceIndex)
                    }
                    item={item}
                    index={evidenceIndex}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
