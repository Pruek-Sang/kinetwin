import { useEffect, useRef, useState } from "react";
import type { OverlayData } from "../api";
import { HandOverlay } from "./HandOverlay";
import { ReferenceSkeletonPlayer } from "./ReferenceSkeletonPlayer";

interface Props {
  patientUrl: string;
  overlay: OverlayData | null;
  /** when true, keep the reference + patient roughly in sync on play */
  syncKey: number;
}

/**
 * Split-screen player: PATIENT video on the left (with a tracked-hand skeleton
 * overlay), the ideal REFERENCE (3D skeleton animation from trajectory JSON)
 * on the right. One play/pause control drives both so the viewer can compare
 * side-by-side.
 */
export function SplitScreen({ patientUrl, overlay, syncKey }: Props) {
  const patientRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  // restart both when a new patient video is chosen
  useEffect(() => {
    const v = patientRef.current;
    if (v) v.currentTime = 0;
    setPlaying(false);
  }, [syncKey]);

  function toggle() {
    const p = patientRef.current;
    if (!p) {
      // No patient video yet? Just toggle the reference skeleton
      setPlaying((prev) => !prev);
      return;
    }
    if (playing) {
      p.pause();
      setPlaying(false);
    } else {
      void p.play();
      setPlaying(true);
    }
  }

  return (
    <div className="rounded-2xl border border-kt-edge bg-kt-panel overflow-hidden">
      <div className="grid grid-cols-2 gap-px bg-kt-edge">
        <Panel label="PATIENT" tone="text-kt-amber">
          {patientUrl ? (
            <div className="relative h-full w-full bg-black">
              <video
                ref={patientRef}
                src={patientUrl}
                className="h-full w-full object-contain"
                playsInline
                muted
              />
              <HandOverlay videoRef={patientRef} overlay={overlay} />
            </div>
          ) : (
            <Placeholder text="Upload a patient task video" />
          )}
        </Panel>
        <Panel label="REFERENCE · 3D Skeleton" tone="text-kt-cyan">
          <ReferenceSkeletonPlayer playing={playing} />
        </Panel>
      </div>
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-xs uppercase tracking-wider text-kt-muted">
          Side-by-side comparison · Trajectory-driven 3D skeleton
        </span>
        <button
          onClick={toggle}
          className="rounded-lg bg-kt-cyan/15 px-4 py-1.5 text-sm font-semibold text-kt-cyan ring-1 ring-kt-cyan/40 transition hover:bg-kt-cyan/25"
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
      </div>
    </div>
  );
}

function Panel({
  label,
  tone,
  children,
}: {
  label: string;
  tone: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-kt-panel">
      <div className={`px-3 py-1.5 text-[11px] font-semibold tracking-wider ${tone}`}>
        {label}
      </div>
      <div className="h-[500px] w-full bg-black">{children}</div>
    </div>
  );
}

function Placeholder({ text }: { text: string }) {
  return (
    <div className="flex h-full w-full items-center justify-center text-sm text-kt-muted">
      {text}
    </div>
  );
}
