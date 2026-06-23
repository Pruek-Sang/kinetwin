// Thin API client for the KineTwin backend.
// API base is empty in dev/prod so requests go same-origin (the Vite dev server
// proxies /analyze* and /health to the FastAPI backend on :8000).
const API = import.meta.env.VITE_API_URL ?? "";

export interface OverlayData {
  fps: number;
  frames: (number[][] | null)[]; // each frame: 21 [x,y] in [0,1], or null
  landmark_colors?: string[]; // per-landmark: "cyan" | "amber" | "red" (from backend)
}

export interface OneReport {
  score: { speed: number; accuracy: number; quality: number; composite: number };
  raw: Record<string, number>;
  vs_reference: {
    speed_ratio: number;
    slower_than_normal_pct: number;
    smoother_ratio: number;
  };
  overlay?: OverlayData;
}

export async function analyzeOne(video: File): Promise<OneReport> {
  const fd = new FormData();
  fd.append("video", video);
  const r = await fetch(`${API}/analyze-one`, { method: "POST", body: fd });
  if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`);
  return (await r.json()) as OneReport;
}

export async function health(): Promise<boolean> {
  try {
    const r = await fetch(`${API}/health`);
    return r.ok;
  } catch {
    return false;
  }
}
