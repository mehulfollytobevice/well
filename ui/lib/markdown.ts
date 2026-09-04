/** Repair pdfplumber-style pipe grids so GFM can render them as tables. */

function splitCells(line: string): string[] {
  let trimmed = line.trim();
  if (!trimmed.includes("|")) return [trimmed];
  if (!trimmed.startsWith("|")) trimmed = `| ${trimmed}`;
  if (!trimmed.endsWith("|")) trimmed = `${trimmed} |`;
  return trimmed
    .split("|")
    .slice(1, -1)
    .map((cell) => cell.trim());
}

function isDelimiterRow(cells: string[]): boolean {
  return cells.length > 0 && cells.every((cell) => !cell || /^:?-{2,}:?$/.test(cell));
}

function isTableishLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.includes("|")) return false;
  const cells = splitCells(trimmed);
  return cells.length >= 2 || trimmed.startsWith("|");
}

function compactColumns(rows: string[][]): string[][] {
  if (rows.length === 0) return rows;
  const width = Math.max(...rows.map((row) => row.length));
  const padded = rows.map((row) => {
    const next = [...row];
    while (next.length < width) next.push("");
    return next;
  });
  const keep: number[] = [];
  for (let col = 0; col < width; col += 1) {
    const filled = padded.some((row) => row[col]?.trim() && !/^:?-{2,}:?$/.test(row[col]));
    if (filled) keep.push(col);
  }
  if (keep.length === 0) return [];
  return padded
    .map((row) => keep.map((index) => row[index] ?? ""))
    .filter((row) => row.some((cell) => cell.trim() && !/^:?-{2,}:?$/.test(cell)));
}

function rowsToMarkdown(rows: string[][]): string {
  const data = compactColumns(rows.filter((row) => !isDelimiterRow(row)));
  if (data.length === 0) return "";

  const nonemptyCounts = data.map((row) => row.filter((cell) => cell.trim()).length);
  if (nonemptyCounts.every((count) => count <= 1)) {
    return data.map((row) => row.find((cell) => cell.trim()) ?? "").join("\n\n");
  }

  const width = Math.max(...data.map((row) => row.length));
  const padded = data.map((row) => {
    const next = [...row];
    while (next.length < width) next.push("");
    return next;
  });
  const header = padded[0];
  const delimiter = header.map(() => "---");
  const lines = [
    `| ${header.join(" | ")} |`,
    `| ${delimiter.join(" | ")} |`,
    ...padded.slice(1).map((row) => `| ${row.join(" | ")} |`),
  ];
  return lines.join("\n");
}

export function normalizeEvidenceMarkdown(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let tableRows: string[][] = [];

  const flush = () => {
    if (tableRows.length === 0) return;
    const block = rowsToMarkdown(tableRows);
    if (block) out.push(block);
    tableRows = [];
  };

  for (const line of lines) {
    if (isTableishLine(line)) {
      tableRows.push(splitCells(line));
      continue;
    }
    flush();
    out.push(line);
  }
  flush();
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}
