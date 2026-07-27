import type { RunData, RunInsights } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export async function getSamples(): Promise<Record<string, RunData>> {
  const res = await fetch(`${API_URL}/api/samples`);
  if (!res.ok) throw new Error(`Could not load samples (${res.status})`);
  return res.json();
}

export async function analyze(run: RunData): Promise<RunInsights> {
  const res = await fetch(`${API_URL}/api/insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(run),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}
