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

  try {
    const upstream = await fetch(`${API_URL}/api/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Upstream API unavailable" }, { status: 502 });
  }
}
