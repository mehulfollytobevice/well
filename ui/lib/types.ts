export type Claim = {
  text: string;
  source_ids: string[];
};

export type SqlEvidence = {
  kind: "sql";
  evidence_id: string;
  query_id: string;
  metric_id: string | null;
  sql: string;
  row_count: number;
  rows: Record<string, unknown>[];
  source: string;
};

export type RagEvidence = {
  kind: "rag";
  evidence_id: string;
  chunk_id: string;
  doc_id: string;
  title: string;
  page: number;
  excerpt: string;
  well_ids: string[];
  score: number;
};

export type AgentResponse = {
  status: "answered" | "refused" | "needs_clarification";
  route: string;
  claims: Claim[];
  evidence: Array<SqlEvidence | RagEvidence>;
  refusal_reason?: string | null;
  verifier_notes?: string | null;
};
