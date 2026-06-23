import { RefObject, useEffect, useMemo, useRef } from "react";
import { HAND_CONNECTIONS } from "../landmarks";
import type { OverlayData } from "../api";

/**
 * Draws the tracked 21-landmark hand skeleton on a canvas over the patient
 * <video>, with PER-LANDMARK colour coding:
 *
 *   cyan  = stable (smooth, low jitter)
 *   amber = borderline
 *   red   = unstable (high frame-to-frame jitter — tremor / compensatory)
 *
 * Also draws a forearm extension (wrist → estimated elbow direction) and a
 * dashed bounding box with "HAND TRACKED" label.
 *
 * For a NORMAL hand all points are blue. For an IMPAIRED hand, specific
 * fingers/landmarks turn red — showing WHERE the weakness is.
 */
export function HandOverlay({
  videoRef,
  overlay,
}: {
  videoRef: RefObject<HTMLVideoElement>;
  overlay: OverlayData | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // ── Per-landmark stability (computed once from all frames) ──
  const stability = useMemo<number[] | null>(() => {
    if (!overlay || overlay.frames.length < 3) return null;
    const N = 21;
    const deltas: number[] = new Array(N).fill(0);
    let count = 0;
    for (let t = 1; t < overlay.frames.length; t++) {
      const prev = overlay.frames[t - 1];
      const curr = overlay.frames[t];
      if (!prev || !curr) continue;
      for (let i = 0; i < N; i++) {
        const dx = curr[i][0] - prev[i][0];
        const dy = curr[i][1] - prev[i][1];
        deltas[i] += Math.hypot(dx, dy);
      }
      count++;
    }
    if (count === 0) return null;
    const avg = deltas.reduce((a, b) => a + b, 0) / N / count;
    if (avg < 1e-9) return null;
    // ratio: 1.0 = average movement; >1.5 = much more jittery than average
    return deltas.map((d) => (d / count) / avg);
  }, [overlay]);

  // ── Colour by stability ratio (neon vibrant colours) ──
  function pointColor(i: number): string {
    if (!stability) return "#00e5ff"; // neon cyan
    const r = stability[i] ?? 1;
    if (r > 1.3) return "#ff1744";   // hot red
    if (r > 1.1) return "#ffb300";   // bright amber
    return "#00e5ff";                 // neon cyan
  }

  function connColor(a: number, b: number): string {
    if (!stability) return "#00e5ff";
    const r = Math.max(stability[a] ?? 1, stability[b] ?? 1);
    if (r > 1.3) return "#ff1744";
    if (r > 1.1) return "#ffb300";
    return "#00e5ff";
  }

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !overlay) return;

    const ctx = canvas.getContext("2d")!;
    let raf = 0;

    const draw = () => {
      const w = video.clientWidth;
      const h = video.clientHeight;
      if (w === 0 || h === 0) { raf = requestAnimationFrame(draw); return; }
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      ctx.clearRect(0, 0, w, h);

      // letterbox mapping (object-contain)
      const vw = video.videoWidth || 16;
      const vh = video.videoHeight || 9;
      const vr = vw / vh;
      const cr = w / h;
      let dw: number, dh: number, ox: number, oy: number;
      if (vr > cr) { dw = w; dh = w / vr; ox = 0; oy = (h - dh) / 2; }
      else { dh = h; dw = h * vr; ox = (w - dw) / 2; oy = (h - dh) / 2; }

      const fi = Math.round(video.currentTime * overlay.fps);
      const lm = overlay.frames[Math.max(0, Math.min(overlay.frames.length - 1, fi))];
      if (!lm) { raf = requestAnimationFrame(draw); return; }

      const px = lm.map((p) => [ox + p[0] * dw, oy + p[1] * dh]);

      // ── Bounding box ──
      const xs = px.map((p) => p[0]);
      const ys = px.map((p) => p[1]);
      const pad = Math.max(8, dw * 0.02);
      ctx.save();
      ctx.strokeStyle = "rgba(34,211,238,0.5)";
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 4]);
      ctx.strokeRect(
        Math.min(...xs) - pad, Math.min(...ys) - pad,
        Math.max(...xs) - Math.min(...xs) + pad * 2,
        Math.max(...ys) - Math.min(...ys) + pad * 2,
      );
      ctx.setLineDash([]);
      ctx.fillStyle = "#22d3ee";
      ctx.font = `${Math.max(11, dw * 0.025)}px monospace`;
      ctx.fillText("HAND TRACKED", Math.min(...xs) - pad, Math.min(...ys) - pad - 4);
      ctx.restore();

      // ── Forearm extension (wrist → away from fingers, ~half arm) ──
      const wrist = px[0];
      const midMCP = px[9];
      const faDx = wrist[0] - midMCP[0];
      const faDy = wrist[1] - midMCP[1];
      const faLen = Math.hypot(faDx, faDy);
      if (faLen > 1) {
        const ux = faDx / faLen;
        const uy = faDy / faLen;
        const extLen = faLen * 1.8;
        const ex = wrist[0] + ux * extLen;
        const ey = wrist[1] + uy * extLen;
        const faColor = pointColor(0);
        ctx.globalCompositeOperation = "lighter";
        ctx.strokeStyle = faColor + "25"; ctx.lineWidth = Math.max(3, dw * 0.006) * 3;
        ctx.beginPath(); ctx.moveTo(wrist[0], wrist[1]); ctx.lineTo(ex, ey); ctx.stroke();
        ctx.strokeStyle = faColor; ctx.lineWidth = Math.max(3, dw * 0.006);
        ctx.beginPath(); ctx.moveTo(wrist[0], wrist[1]); ctx.lineTo(ex, ey); ctx.stroke();
        ctx.globalCompositeOperation = "source-over";
        for (let k = 0.3; k <= 1; k += 0.3) {
          const dx2 = wrist[0] + ux * extLen * k;
          const dy2 = wrist[1] + uy * extLen * k;
          ctx.fillStyle = faColor;
          ctx.beginPath();
          ctx.arc(dx2, dy2, Math.max(3, dw * 0.006), 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // ── Neon skeleton connections (triple-pass: wide glow → mid → bright core) ──
      ctx.globalCompositeOperation = "lighter"; // additive → colours pop like neon
      const baseW = Math.max(3, dw * 0.008);
      for (const [a, b] of HAND_CONNECTIONS) {
        const c = connColor(a, b);
        // wide glow
        ctx.strokeStyle = c + "25";
        ctx.lineWidth = baseW * 3.5;
        ctx.beginPath(); ctx.moveTo(px[a][0], px[a][1]); ctx.lineTo(px[b][0], px[b][1]); ctx.stroke();
        // mid glow
        ctx.strokeStyle = c + "55";
        ctx.lineWidth = baseW * 2;
        ctx.beginPath(); ctx.moveTo(px[a][0], px[a][1]); ctx.lineTo(px[b][0], px[b][1]); ctx.stroke();
        // bright core
        ctx.strokeStyle = c;
        ctx.lineWidth = baseW;
        ctx.beginPath(); ctx.moveTo(px[a][0], px[a][1]); ctx.lineTo(px[b][0], px[b][1]); ctx.stroke();
      }

      // ── Glossy orb points (halo → core → white highlight = 3D sphere) ──
      const pr = Math.max(4, dw * 0.009);
      for (let i = 0; i < px.length; i++) {
        const c = pointColor(i);
        const x = px[i][0], y = px[i][1];
        // outer halo
        ctx.fillStyle = c + "30";
        ctx.beginPath(); ctx.arc(x, y, pr * 2.8, 0, Math.PI * 2); ctx.fill();
        // mid glow
        ctx.fillStyle = c + "70";
        ctx.beginPath(); ctx.arc(x, y, pr * 1.6, 0, Math.PI * 2); ctx.fill();
        // bright core
        ctx.fillStyle = c;
        ctx.beginPath(); ctx.arc(x, y, pr, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
      // white highlights (glossy 3D look — drawn on top, normal blend)
      for (let i = 0; i < px.length; i++) {
        const x = px[i][0], y = px[i][1];
        ctx.fillStyle = "rgba(255,255,255,0.85)";
        ctx.beginPath(); ctx.arc(x - pr * 0.3, y - pr * 0.3, pr * 0.35, 0, Math.PI * 2); ctx.fill();
      }
      ctx.shadowBlur = 0;

      // ── Legend ──
      const legX = ox + 8;
      const legY = oy + dh - 60;
      ctx.font = `${Math.max(10, dw * 0.02)}px monospace`;
      [["#00e5ff", "stable"], ["#ffb300", "borderline"], ["#ff1744", "unstable"]].forEach(
        ([c, label], idx) => {
          ctx.fillStyle = c as string;
          ctx.beginPath();
          ctx.arc(legX, legY + idx * 16, 4, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "rgba(255,255,255,0.7)";
          ctx.fillText(label as string, legX + 10, legY + idx * 16 + 4);
        },
      );

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [overlay, stability, videoRef]);

  if (!overlay) return null;
  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}
