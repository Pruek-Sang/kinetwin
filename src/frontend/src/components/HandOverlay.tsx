import { RefObject, useEffect, useRef } from "react";
import { HAND_CONNECTIONS } from "../landmarks";
import type { OverlayData } from "../api";

const COLOR_MAP: Record<string, string> = {
  cyan: "#00e5ff",
  amber: "#ffb300",
  red: "#ff1744",
};

/**
 * Draws the tracked 21-landmark hand skeleton on a canvas over the patient
 * <video>. Colours come PRE-COMPUTED from the backend (compared against the
 * normal-hand reference, not self-referential):
 *
 *   cyan  = stable (matches normal)
 *   amber = borderline (1.2-1.5× more jittery than normal)
 *   red   = unstable (>1.5× more jittery — tremor / weakness)
 *
 * Lines: flat solid strokes (no neon). Points: glossy 3D orbs with halo +
 * bright core + white highlight.
 */
export function HandOverlay({
  videoRef,
  overlay,
}: {
  videoRef: RefObject<HTMLVideoElement>;
  overlay: OverlayData | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !overlay) return;

    const colors = overlay.landmark_colors ?? [];
    const ptColor = (i: number) => COLOR_MAP[colors[i] ?? "cyan"] ?? COLOR_MAP.cyan;
    const lnColor = (a: number, b: number) => {
      const ca = colors[a] ?? "cyan";
      const cb = colors[b] ?? "cyan";
      // line takes the WORSE colour of its two endpoints
      const rank = { cyan: 0, amber: 1, red: 2 };
      const worse = rank[ca] >= rank[cb] ? ca : cb;
      return COLOR_MAP[worse] ?? COLOR_MAP.cyan;
    };

    const ctx = canvas.getContext("2d")!;
    let raf = 0;

    const draw = () => {
      const w = video.clientWidth;
      const h = video.clientHeight;
      if (w === 0 || h === 0) { raf = requestAnimationFrame(draw); return; }
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      ctx.clearRect(0, 0, w, h);

      // letterbox
      const vw = video.videoWidth || 16, vh = video.videoHeight || 9;
      const vr = vw / vh, cr = w / h;
      let dw, dh, ox, oy;
      if (vr > cr) { dw = w; dh = w / vr; ox = 0; oy = (h - dh) / 2; }
      else { dh = h; dw = h * vr; ox = (w - dw) / 2; oy = (h - dh) / 2; }

      const fi = Math.round(video.currentTime * overlay.fps);
      const lm = overlay.frames[Math.max(0, Math.min(overlay.frames.length - 1, fi))];
      if (!lm) { raf = requestAnimationFrame(draw); return; }
      const px = lm.map((p) => [ox + p[0] * dw, oy + p[1] * dh]);

      // ── Bounding box ──
      const xs = px.map((p) => p[0]), ys = px.map((p) => p[1]);
      const pad = Math.max(8, dw * 0.02);
      ctx.save();
      ctx.strokeStyle = "rgba(0,229,255,0.4)";
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 4]);
      ctx.strokeRect(Math.min(...xs) - pad, Math.min(...ys) - pad,
        Math.max(...xs) - Math.min(...xs) + pad * 2,
        Math.max(...ys) - Math.min(...ys) + pad * 2);
      ctx.setLineDash([]);
      ctx.fillStyle = "#00e5ff";
      ctx.font = `${Math.max(11, dw * 0.025)}px monospace`;
      ctx.fillText("HAND TRACKED", Math.min(...xs) - pad, Math.min(...ys) - pad - 4);
      ctx.restore();

      // ── Forearm extension (wrist → half arm, flat line + dots) ──
      const w0 = px[0], m9 = px[9];
      const faDx = w0[0] - m9[0], faDy = w0[1] - m9[1];
      const faLen = Math.hypot(faDx, faDy);
      if (faLen > 1) {
        const ux = faDx / faLen, uy = faDy / faLen, ext = faLen * 1.8;
        const faC = ptColor(0);
        ctx.strokeStyle = faC;
        ctx.lineWidth = Math.max(3, dw * 0.006);
        ctx.beginPath(); ctx.moveTo(w0[0], w0[1]); ctx.lineTo(w0[0] + ux * ext, w0[1] + uy * ext); ctx.stroke();
        for (let k = 0.3; k <= 1; k += 0.3) {
          ctx.fillStyle = faC;
          ctx.beginPath();
          ctx.arc(w0[0] + ux * ext * k, w0[1] + uy * ext * k, Math.max(3, dw * 0.005), 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // ── Skeleton lines: FLAT solid strokes (no neon) ──
      ctx.lineWidth = Math.max(2.5, dw * 0.006);
      for (const [a, b] of HAND_CONNECTIONS) {
        ctx.strokeStyle = lnColor(a, b);
        ctx.beginPath();
        ctx.moveTo(px[a][0], px[a][1]);
        ctx.lineTo(px[b][0], px[b][1]);
        ctx.stroke();
      }

      // ── Points: glossy 3D orbs (halo + core + highlight) ──
      const pr = Math.max(4, dw * 0.009);
      for (let i = 0; i < px.length; i++) {
        const c = ptColor(i);
        const x = px[i][0], y = px[i][1];
        // halo
        ctx.fillStyle = c + "30";
        ctx.beginPath(); ctx.arc(x, y, pr * 2.5, 0, Math.PI * 2); ctx.fill();
        // core
        ctx.fillStyle = c;
        ctx.beginPath(); ctx.arc(x, y, pr, 0, Math.PI * 2); ctx.fill();
        // white highlight (3D glossy)
        ctx.fillStyle = "rgba(255,255,255,0.8)";
        ctx.beginPath(); ctx.arc(x - pr * 0.3, y - pr * 0.3, pr * 0.35, 0, Math.PI * 2); ctx.fill();
      }

      // ── Legend ──
      const legX = ox + 8, legY = oy + dh - 60;
      ctx.font = `${Math.max(10, dw * 0.02)}px monospace`;
      (["cyan", "amber", "red"] as const).forEach((key, idx) => {
        const c = COLOR_MAP[key];
        ctx.fillStyle = c;
        ctx.beginPath(); ctx.arc(legX, legY + idx * 16, 4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,0.7)";
        ctx.fillText(key, legX + 10, legY + idx * 16 + 4);
      });

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [overlay, videoRef]);

  if (!overlay) return null;
  return <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />;
}
