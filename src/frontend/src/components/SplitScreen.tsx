import { useEffect, useRef, useState } from "react";

interface Props {
  patientUrl: string;
  /** when true, keep the reference + patient roughly in sync on play */
  syncKey: number;
}

/**
 * Split-screen player: PATIENT video on the left, the ideal REFERENCE
 * (kinematic skeleton) on the right. One play/pause control drives both so the
 * viewer can compare speed side-by-side.
 */
export function SplitScreen({ patientUrl, syncKey }: Props) {
  const patientRef = useRef<HTMLVideoElement>(null);
  const refRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  // restart both when a new patient video is chosen
  useEffect(() => {
    [patientRef.current, refRef.current].forEach((v) => {
      if (!v) return;
      v.currentTime = 0;
    });
    setPlaying(false);
  }, [syncKey]);

  function toggle() {
    const p = patientRef.current;
    const r = refRef.current;
    if (!p || !r) return;
    if (playing) {
      p.pause();
      r.pause();
      setPlaying(false);
    } else {
      void p.play();
      void r.play();
      setPlaying(true);
    }
  }

  return (
    <div className="rounded-2xl border border-kt-edge bg-kt-panel overflow-hidden">
      <div className="grid grid-cols-2 gap-px bg-kt-edge">
        <Panel label="PATIENT" tone="text-kt-amber">
          {patientUrl ? (
            <video
              ref={patientRef}
              src={patientUrl}
              className="h-full w-full object-contain bg-black"
              playsInline
            />
          ) : (
            <Placeholder text="Upload a patient task video" />
          )}
        </Panel>
        <Panel label="REFERENCE (normal)" tone="text-kt-cyan">
          <video
            ref={refRef}
            src="/reference.mp4"
            className="h-full w-full object-contain bg-black"
            loop
            muted
            playsInline
          />
        </Panel>
      </div>
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-xs uppercase tracking-wider text-kt-muted">
          Side-by-side comparison
        </span>
        <button
          onClick={toggle}
          disabled={!patientUrl}
          className="rounded-lg bg-kt-cyan/15 px-4 py-1.5 text-sm font-semibold text-kt-cyan ring-1 ring-kt-cyan/40 transition hover:bg-kt-cyan/25 disabled:opacity-40"
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
      <div className="aspect-video w-full bg-black">{children}</div>
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
