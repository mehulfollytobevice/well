"use client";

import type { RagEvidence, SqlEvidence } from "@/lib/types";
import { formatScore } from "@/lib/format";
import { MarkdownExcerpt } from "@/components/MarkdownExcerpt";

type EvidenceCardProps = {
  item: SqlEvidence | RagEvidence;
  index: number;
};

function sourceBadge(kind: "sql" | "rag") {
  return kind === "sql" ? "SQL" : "PDF";
}

function sqlTitle(item: SqlEvidence): string {
  if (item.metric_id) return item.metric_id.replace(/_/g, " ");
  if (item.sql) {
    const match = item.sql.match(/FROM\s+(\w+)/i);
    if (match) return `Query on ${match[1]}`;
  }
  return "Database query";
}

function sqlSubtitle(item: SqlEvidence): string {
  const parts = [`${item.row_count} row${item.row_count === 1 ? "" : "s"}`];
  if (item.source) parts.push(item.source);
  return parts.join(" · ");
}

export function EvidenceCard({ item, index }: EvidenceCardProps) {
  const badge = sourceBadge(item.kind);
  const sourceNum = index + 1;

  if (item.kind === "rag") {
    return (
      <details className="evidence-card evidence-card--pdf" open={index === 0}>
        <summary className="evidence-card__header">
          <span className={`evidence-badge evidence-badge--${item.kind}`}>{badge}</span>
          <span className="evidence-card__title-group">
            <span className="evidence-card__label">Source {sourceNum}</span>
            <span className="evidence-card__title">{item.title}</span>
          </span>
          <span className="evidence-card__chevron" aria-hidden="true" />
        </summary>
        <div className="evidence-card__body evidence-card__body--pdf">
          <div className="evidence-meta">
            <span className="evidence-meta__item">
              <span className="evidence-meta__label">Page</span>
              <span className="evidence-meta__value">{item.page}</span>
            </span>
            <span className="evidence-meta__item">
              <span className="evidence-meta__label">Relevance</span>
              <span className="evidence-meta__value">{formatScore(item.score)}</span>
            </span>
            {item.well_ids.length > 0 && (
              <span className="evidence-meta__item">
                <span className="evidence-meta__label">Wells</span>
                <span className="evidence-meta__value">{item.well_ids.join(", ")}</span>
              </span>
            )}
            {item.section && (
              <span className="evidence-meta__item">
                <span className="evidence-meta__label">Section</span>
                <span className="evidence-meta__value">{item.section}</span>
              </span>
            )}
          </div>
          <MarkdownExcerpt markdown={item.excerpt} />
        </div>
      </details>
    );
  }

  return (
    <details className="evidence-card evidence-card--sql" open={index === 0}>
      <summary className="evidence-card__header">
        <span className={`evidence-badge evidence-badge--${item.kind}`}>{badge}</span>
        <span className="evidence-card__title-group">
          <span className="evidence-card__label">Source {sourceNum}</span>
          <span className="evidence-card__title">{sqlTitle(item)}</span>
          <span className="evidence-card__subtitle">{sqlSubtitle(item)}</span>
        </span>
        <span className="evidence-card__chevron" aria-hidden="true" />
      </summary>
      <div className="evidence-card__body">
        {item.sql && (
          <div className="evidence-sql">
            <span className="evidence-sql__label">Query</span>
            <pre className="evidence-json">{item.sql}</pre>
          </div>
        )}
        <div className="evidence-json-wrap">
          <span className="evidence-sql__label">Results</span>
          <pre className="evidence-json">{JSON.stringify(item.rows.slice(0, 5), null, 2)}</pre>
        </div>
        {item.rows.length > 5 && (
          <p className="evidence-truncated">
            Showing 5 of {item.row_count} rows
          </p>
        )}
      </div>
    </details>
  );
}
