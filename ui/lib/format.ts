export function formatLatency(ms: number): string {
  const seconds = ms / 1000;
  return seconds < 10 ? `${seconds.toFixed(1)} s` : `${Math.round(seconds)} s`;
}

export function formatScore(score: number): string {
  return `${Math.round(score * 100)}% match`;
}
