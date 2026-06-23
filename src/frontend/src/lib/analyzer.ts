/**
 * KineTwin browser-side analyzer — REAL MediaPipe Web tracking + metrics.
 *
 * Flow: video plays → MediaPipe Web detects 21 landmarks per frame →
 * compute per-landmark stability colours (vs reference) + metrics →
 * optionally send landmarks to backend for AI classifier prediction.
 *
 * No pre-baked data. No mock. Everything computed live in the browser.
 */
import { HandLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import type { OneReport, OverlayData } from "../api";

// ── Reference constants (from normal hand video, Python-computed once) ──
const REF_DELTAS: number[] = [
  0.00538538, 0.00549880, 0.00602040, 0.00671665, 0.00804168,
  0.00553001, 0.00584381, 0.00717193, 0.00935620, 0.00566343,
  0.00654213, 0.00782539, 0.00944310, 0.00577780, 0.00704722,
  0.00786851, 0.00897062, 0.00607123, 0.00762400, 0.00841938,
  0.00914419,
];
const REF_MEAN_SPEED = 0.11705452;
const REF_DIM_JERK = 182262987.7;
const QUALITY_MARGIN = 1.5;
const SPEED_MARGIN = 1.5;
const SMOOTH_WINDOW = 11;
const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17],
];

// ── MediaPipe Web singleton ──
let _landmarker: HandLandmarker | null = null;

async function getLandmarker(): Promise<HandLandmarker> {
  if (_landmarker) return _landmarker;
  const fileset = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm"
  );
  _landmarker = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numHands: 1,
    minHandDetectionConfidence: 0.5,
    minHandPresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
  return _landmarker;
}

// ── Math helpers (ported from Python metrics) ──

function smooth(points: number[][], window: number): number[][] {
  if (window <= 1 || points.length < window) return points;
  return points.map((_, i) => {
    const start = Math.max(0, i - Math.floor(window / 2));
    const end = Math.min(points.length, start + window);
    const slice = points.slice(start, end);
    return [
      slice.reduce((s, p) => s + p[0], 0) / slice.length,
      slice.reduce((s, p) => s + p[1], 0) / slice.length,
    ];
  });
}

function pathLength(pts: number[][]): number {
  let len = 0;
  for (let i = 1; i < pts.length; i++) {
    len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  }
  return len;
}

function derivative(pts: number[][], dt: number, order: number): number[][] {
  let arr = pts.map((p) => [...p]);
  for (let o = 0; o < order; o++) {
    const next: number[][] = [];
    for (let i = 0; i < arr.length; i++) {
      const prev = arr[Math.max(0, i - 1)];
      const curr = arr[Math.min(arr.length - 1, i + 1)];
      next.push([(curr[0] - prev[0]) / (2 * dt), (curr[1] - prev[1]) / (2 * dt)]);
    }
    arr = next;
  }
  return arr;
}

// ── Per-landmark stability colours ──

function computeDeltas(frames: (number[][] | null)[]): number[] {
  const deltas = new Array(21).fill(0);
  let count = 0;
  for (let t = 1; t < frames.length; t++) {
    if (frames[t] && frames[t - 1]) {
      for (let i = 0; i < 21; i++) {
        const dx = frames[t]![i][0] - frames[t - 1]![i][0];
        const dy = frames[t]![i][1] - frames[t - 1]![i][1];
        deltas[i] += Math.hypot(dx, dy);
      }
      count++;
    }
  }
  return deltas.map((d) => (count > 0 ? d / count : 0));
}

function colorsFromDeltas(deltas: number[]): string[] {
  return deltas.map((d, i) => {
    const ref = REF_DELTAS[i] || 1e-9;
    const ratio = d / ref;
    if (ratio > 1.5) return "red";
    if (ratio > 1.2) return "amber";
    return "cyan";
  });
}

// ── Metrics (wrist = landmark 0, 2D image coords) ──

function computeMetrics(frames: (number[][] | null)[], fps: number) {
  const wristRaw: number[][] = [];
  for (const f of frames) {
    if (f) wristRaw.push([f[0][0], f[0][1]]);
  }
  if (wristRaw.length < 2) return { meanSpeed: 0, straightness: 1, dimJerk: Infinity, peaks: 0 };

  const pts = smooth(wristRaw, SMOOTH_WINDOW);
  const dt = 1 / fps;
  const duration = (pts.length - 1) / fps;

  // Speed
  const pLen = pathLength(pts);
  const meanSpeed = duration > 0 ? pLen / duration : 0;

  // Accuracy (straightness)
  const netDisp = Math.hypot(
    pts[pts.length - 1][0] - pts[0][0],
    pts[pts.length - 1][1] - pts[0][1]
  );
  const straightness = pLen > 1e-9 ? Math.min(1, netDisp / pLen) : 1;

  // Quality (dimensionless jerk)
  const jerk = derivative(pts, dt, 3);
  let msj = 0;
  for (const j of jerk) msj += j[0] * j[0] + j[1] * j[1];
  msj /= jerk.length;
  const dimJerk =
    duration > 1e-9 && netDisp > 1e-9 ? (msj * Math.pow(duration, 6)) / (netDisp * netDisp) : Infinity;

  // Velocity peaks
  const vel: number[] = [];
  for (let i = 1; i < pts.length; i++) {
    vel.push(Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) / dt);
  }
  const peakMax = Math.max(...vel, 1e-9);
  let peaks = 0;
  for (let i = 1; i < vel.length - 1; i++) {
    if (vel[i] > vel[i - 1] && vel[i] >= vel[i + 1] && vel[i] >= peakMax * 0.15) peaks++;
  }

  return { meanSpeed, straightness, dimJerk, peaks };
}

function scoreFromMetrics(m: ReturnType<typeof computeMetrics>) {
  const speedScore = m.meanSpeed > 0 ? Math.min(1, (m.meanSpeed * SPEED_MARGIN) / REF_MEAN_SPEED) * 100 : 0;
  const accScore = Math.min(1, m.straightness) * 100;
  const qualScore =
    m.dimJerk > 0 && isFinite(m.dimJerk)
      ? Math.min(1, (REF_DIM_JERK * QUALITY_MARGIN) / m.dimJerk) * 100
      : 0;
  const composite = speedScore * 0.2 + accScore * 0.1 + qualScore * 0.7;

  return { speed: speedScore, accuracy: accScore, quality: qualScore, composite };
}

// ── Main: track video frame by frame ──

export async function analyzeVideo(
  video: HTMLVideoElement,
  onProgress?: (overlay: OverlayData) => void
): Promise<{ overlay: OverlayData; report: Omit<OneReport, "overlay"> }> {
  const landmarker = await getLandmarker();
  const fps = 30;
  const totalFrames = Math.max(2, Math.ceil(video.duration * fps));
  const frames: (number[][] | null)[] = [];

  // Seek through every frame
  for (let i = 0; i < totalFrames; i++) {
    video.currentTime = Math.min(i / fps, video.duration - 0.001);
    await new Promise<void>((resolve) => {
      const handler = () => {
        video.removeEventListener("seeked", handler);
        resolve();
      };
      video.addEventListener("seeked", handler);
      // Timeout fallback
      setTimeout(() => { video.removeEventListener("seeked", handler); resolve(); }, 200);
    });

    const result = landmarker.detectForVideo(video, performance.now());
    if (result.landmarks && result.landmarks.length > 0) {
      frames.push(result.landmarks[0].map((p) => [p.x, p.y] as [number, number]));
    } else {
      frames.push(null);
    }

    // Progressive overlay update (all-cyan during tracking)
    if (onProgress && i % 10 === 0) {
      onProgress({ fps, frames: [...frames], landmark_colors: new Array(21).fill("cyan") });
    }
  }

  // Compute final results
  const deltas = computeDeltas(frames);
  const colors = colorsFromDeltas(deltas);
  const overlay: OverlayData = { fps, frames, landmark_colors: colors };

  const metrics = computeMetrics(frames, fps);
  const scores = scoreFromMetrics(metrics);
  const speedRatio = metrics.meanSpeed / REF_MEAN_SPEED;
  const smootherRatio =
    metrics.dimJerk > 0 && isFinite(metrics.dimJerk) ? REF_DIM_JERK / metrics.dimJerk : 0;

  const report = {
    score: {
      speed: Math.round(scores.speed * 100) / 100,
      accuracy: Math.round(scores.accuracy * 100) / 100,
      quality: Math.round(scores.quality * 100) / 100,
      composite: Math.round(scores.composite * 100) / 100,
    },
    raw: {
      mean_speed: metrics.meanSpeed,
      straightness: metrics.straightness,
      dimensionless_jerk: isFinite(metrics.dimJerk) ? metrics.dimJerk : -1,
      smoothness_index: isFinite(metrics.dimJerk) ? -Math.log(metrics.dimJerk) : -Infinity,
      velocity_peaks: metrics.peaks,
    },
    vs_reference: {
      speed_ratio: Math.round(speedRatio * 1000) / 1000,
      slower_than_normal_pct: Math.round(Math.max(0, (1 - speedRatio) * 100) * 10) / 10,
      smoother_ratio: Math.round(smootherRatio * 1000) / 1000,
    },
  };

  // Final progressive update with real colours
  if (onProgress) onProgress(overlay);

  return { overlay, report };
}

export async function isModelLoaded(): Promise<boolean> {
  try {
    await getLandmarker();
    return true;
  } catch {
    return false;
  }
}
