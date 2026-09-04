import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const ASK_API_KEY = process.env.ASK_API_KEY;

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (ASK_API_KEY) {
    headers.Authorization = `Bearer ${ASK_API_KEY}`;
  }

  const upstreamUrl = `${API_URL}/api/ask`;
  try {
    const upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch (err) {
    const reason = err instanceof Error ? err.message : "fetch failed";
    return NextResponse.json(
      {
        detail: `Upstream API unavailable at ${upstreamUrl} (${reason}). Start FastAPI on port 8000, or set API_URL.`,
      },
      { status: 502 },
    );
  }
}
