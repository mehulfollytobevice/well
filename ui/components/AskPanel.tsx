"use client";

import { useState } from "react";
import type { AgentResponse } from "@/lib/types";

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

  return (
    <section className="panel">
      <form onSubmit={onSubmit}>
        <label htmlFor="question">Question</label>
        <textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" disabled={loading || question.trim().length === 0}>
          {loading ? "Thinking…" : "Ask WellGround"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {response && (
        <div>
          <div className="meta">
            <span className="pill">status: {response.status}</span>
            <span className="pill">route: {response.route}</span>
            {latencyMs !== null && <span className="pill">{latencyMs} ms</span>}
          </div>

          {response.refusal_reason && (
            <p className="error">{response.refusal_reason}</p>
          )}

          {response.claims.map((claim, index) => (
            <p key={index} className="claim">
              {claim.text}
              {claim.source_ids.length > 0 && (
                <em> [{claim.source_ids.join(", ")}]</em>
              )}
            </p>
          ))}

          {response.evidence.length > 0 && (
            <div className="evidence">
              <h3>Evidence</h3>
              {response.evidence.map((item, evidenceIndex) => (
                <details
                  key={
                    item.evidence_id ||
                    (item.kind === "rag" ? item.chunk_id : item.query_id) ||
                    String(evidenceIndex)
                  }>
                  <summary>
                    {item.evidence_id} — {item.kind === "rag" ? item.title : item.query_id}
                  </summary>
                  {item.kind === "rag" ? (
                    <p>
                      Page {item.page} · score {item.score.toFixed(3)}
                      <br />
                      {item.excerpt}
                    </p>
                  ) : (
                    <pre>{JSON.stringify(item.rows.slice(0, 5), null, 2)}</pre>
                  )}
                </details>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
