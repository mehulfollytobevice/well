export function formatLatency(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 10) {
    const n = Number(seconds.toFixed(1));
    return n === 1 ? "1.0 second" : `${n.toFixed(1)} seconds`;
  }
  const rounded = Math.round(seconds);
  return rounded === 1 ? "1 second" : `${rounded} seconds`;
}

export function formatEvidenceCount(count: number): string {
  if (count === 0) return "None found";
  return count === 1 ? "1 source" : `${count} sources`;
}

export function sourceOriginLabel(
  route: string,
  kinds: ReadonlySet<string>,
): string {
  const hasSql = kinds.has("sql");
  const hasRag = kinds.has("rag");
  if (hasSql && hasRag) return "Reports & measurements";
  if (hasSql) return "Well measurements";
  if (hasRag) return "Well reports";
  if (route === "sql") return "Well measurements";
  if (route === "both") return "Reports & measurements";
  if (route === "action") return "Operational request";
  return "Well reports";
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}% match`;
}
