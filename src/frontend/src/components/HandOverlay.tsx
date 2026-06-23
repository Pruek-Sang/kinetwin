import { RefObject, useEffect, useRef } from "react";
import { HAND_CONNECTIONS } from "../landmarks";
import type { OverlayData } from "../api";

/**
 * Draws the tracked 21-landmark hand skeleton on a canvas layered over the
 * patient <video>, synced to playback time. Normalised image coords are mapped
 * through the video's object-contain letterbox so the overlay lines up with the
 * pixels -- this is the "lines comparing the hand" over the footage.
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

    const ctx = canvas.getContext("2d")!;
    let raf = 0;

    const draw = () => {
      const w = video.clientWidth;
      const h = video.clientHeight;
      if (w === 0 || h === 0) {
        raf = requestAnimationFrame(draw);
        return;
      }
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      ctx.clearRect(0, 0, w, h);

      // map normalised [0,1] through object-contain letterbox
      const vw = video.videoWidth || 16;
      const vh = video.videoHeight || 9;
      const vr = vw / vh;
      const cr = w / h;
      let dw: number, dh: number, ox: number, oy: number;
      if (vr > cr) {
        dw = w;
        dh = w / vr;
        ox = 0;
        oy = (h - dh) / 2;
      } else {
        dh = h;
        dw = h * vr;
        ox = (w - dw) / 2;
        oy = (h - dh) / 2;
      }

      const fi = Math.round(video.currentTime * overlay.fps);
      const lm = overlay.frames[Math.max(0, Math.min(overlay.frames.length - 1, fi))];
      if (lm) {
        // --- bounding box around the hand (recognisable "AI tracking" box) ---
        const xs = lm.map((p) => ox + p[0] * dw);
        const ys = lm.map((p) => oy + p[1] * dh);
        const pad = Math.max(8, dw * 0.02);
        const bx0 = Math.min(...xs) - pad;
        const by0 = Math.min(...ys) - pad;
        const bw = Math.max(...xs) - Math.min(...xs) + pad * 2;
        const bh = Math.max(...ys) - Math.min(...ys) + pad * 2;
        ctx.save();
        ctx.strokeStyle = "#22d3ee";
        ctx.lineWidth = Math.max(2, dw * 0.004);
        ctx.setLineDash([8, 4]);
        ctx.strokeRect(bx0, by0, bw, bh);
        ctx.setLineDash([]);
        // label
        ctx.fillStyle = "#22d3ee";
        ctx.font = `${Math.max(11, dw * 0.025)}px monospace`;
        ctx.fillText("HAND TRACKED", bx0, by0 - 4);
        ctx.restore();

        // --- skeleton connections + joints ---
        ctx.lineWidth = Math.max(2, dw * 0.004);
        ctx.strokeStyle = "#22d3ee";
        ctx.shadowColor = "rgba(34,211,238,0.6)";
        ctx.shadowBlur = 6;
        for (const [a, b] of HAND_CONNECTIONS) {
          ctx.beginPath();
          ctx.moveTo(ox + lm[a][0] * dw, oy + lm[a][1] * dh);
          ctx.lineTo(ox + lm[b][0] * dw, oy + lm[b][1] * dh);
          ctx.stroke();
        }
        ctx.shadowBlur = 0;
        ctx.fillStyle = "#e6edf6";
        for (const p of lm) {
          ctx.beginPath();
          ctx.arc(ox + p[0] * dw, oy + p[1] * dh, Math.max(2.5, dw * 0.006), 0, Math.PI * 2);
          ctx.fill();
        }
      }
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [overlay, videoRef]);

  if (!overlay) return null;
  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}
