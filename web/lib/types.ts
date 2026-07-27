// Mirrors the backend Pydantic models (run_insights.models).

export interface Split {
  km: number;
  pace: string; // "m:ss"
  hr: number;
}

export interface RunData {
  splits: Split[];
  distance_km: number;
  elevation_m: number;
}

export interface Flag {
  kind: string;
  detail: string;
}

export interface RunInsights {
  avg_pace: string;
  avg_hr: number;
  split: number;
  fade_pct: number;
  decoupling_pct: number;
  effort_type: string;
  flags: Flag[];
  feedback: string;
  disclaimer: string;
}
