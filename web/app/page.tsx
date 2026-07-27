"use client";

import { useState } from "react";
import { analyze, getSamples } from "../lib/api";
import type { Flag, RunData, RunInsights, Split } from "../lib/types";

// The splits textarea accepts one "km, pace, hr" line per km (pace as m:ss), e.g. "1, 5:12, 148".
function parseSplits(text: string): Split[] {
  const splits: Split[] = [];
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  lines.forEach((line, i) => {
    const parts = line.split(/[,\t]+/).map((p) => p.trim());
    if (parts.length < 3) throw new Error(`Line ${i + 1}: expected "km, pace, hr" (e.g. 1, 5:12, 148).`);
    const [km, pace, hr] = parts;
    if (!/^\d{1,2}:[0-5]\d$/.test(pace)) throw new Error(`Line ${i + 1}: pace "${pace}" must be m:ss.`);
    splits.push({ km: Number(km), pace, hr: Number(hr) });
  });
  return splits;
}

function splitsToText(splits: Split[]): string {
  return splits.map((s) => `${s.km}, ${s.pace}, ${s.hr}`).join("\n");
}

const FLAG_SEV: Record<string, string> = {
  strong_negative_split: "low",
  positive_split: "medium",
  pace_fade: "medium",
  hr_decoupling: "high",
};

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="finding">
      <span className="ct">{label}</span>
      <div style={{ marginTop: 2 }}>{value}</div>
    </div>
  );
}

function FlagCard({ f }: { f: Flag }) {
  const sev = FLAG_SEV[f.kind] ?? "low";
  return (
    <div className={`finding ${sev}`}>
      <div>
        <span className={`sev ${sev}`}>{f.kind.replace(/_/g, " ").toUpperCase()}</span>
      </div>
      <div style={{ marginTop: 4 }}>{f.detail}</div>
    </div>
  );
}

export default function Home() {
  const [splitsText, setSplitsText] = useState("");
  const [distance, setDistance] = useState("8");
  const [elevation, setElevation] = useState("30");
  const [result, setResult] = useState<RunInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const run: RunData = {
        splits: parseSplits(splitsText),
        distance_km: Number(distance),
        elevation_m: Number(elevation),
      };
      if (run.splits.length === 0) throw new Error("Enter at least one split.");
      setResult(await analyze(run));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function loadSample() {
    try {
      const samples = await getSamples();
      const run = samples["positive-split-fade"] ?? Object.values(samples)[0];
      if (!run) return;
      setSplitsText(splitsToText(run.splits));
      setDistance(String(run.distance_km));
      setElevation(String(run.elevation_m));
      setResult(null);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="container">
      <header>
        <h1>run-insights</h1>
        <p>
          Enter a run&rsquo;s per-km splits. A deterministic analyzer computes the split, pace fade, HR
          decoupling and effort type — then a coach note is drafted, grounded in exactly those numbers.
        </p>
      </header>

      <div className="banner">
        ⚠️ Illustrative demo — <strong>not coaching or medical advice</strong>. Summarises objective
        numbers from a single run; it doesn&rsquo;t know your training history, health, or goals. Synthetic data.
      </div>

      <label htmlFor="s">Splits — one &ldquo;km, pace, hr&rdquo; per line (pace as m:ss)</label>
      <textarea
        id="s"
        value={splitsText}
        placeholder={"1, 5:12, 148\n2, 5:10, 150\n3, 5:14, 152"}
        onChange={(e) => setSplitsText(e.target.value)}
      />
      <div className="actions">
        <label style={{ margin: 0 }}>
          distance (km)
          <input className="num" value={distance} onChange={(e) => setDistance(e.target.value)} />
        </label>
        <label style={{ margin: 0 }}>
          elevation (m)
          <input className="num" value={elevation} onChange={(e) => setElevation(e.target.value)} />
        </label>
      </div>
      <div className="actions">
        <button onClick={run} disabled={loading}>{loading ? "Analyzing…" : "Analyze run"}</button>
        <button className="ghost" onClick={loadSample} disabled={loading}>Load sample</button>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="panel">
          <div className="facts">
            <Fact label="avg pace" value={`${result.avg_pace} /km`} />
            <Fact label="avg HR" value={`${result.avg_hr} bpm`} />
            <Fact label="split" value={`${result.split > 0 ? "+" : ""}${result.split}% (${result.split < 0 ? "2nd half faster" : "2nd half slower"})`} />
            <Fact label="pace fade" value={`${result.fade_pct > 0 ? "+" : ""}${result.fade_pct}% (last vs first km)`} />
            <Fact label="HR decoupling" value={`${result.decoupling_pct > 0 ? "+" : ""}${result.decoupling_pct}%`} />
            <Fact label="effort type" value={result.effort_type} />
          </div>

          {result.flags.length === 0 ? (
            <p style={{ color: "var(--good)" }}>Nothing notable to flag — evenly run.</p>
          ) : (
            result.flags.map((f, i) => <FlagCard f={f} key={i} />)
          )}

          {result.feedback && (
            <div className="coach">
              <span className="ct">coach</span>
              <p style={{ margin: "6px 0 0" }}>{result.feedback}</p>
            </div>
          )}

          <p className="disc">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
