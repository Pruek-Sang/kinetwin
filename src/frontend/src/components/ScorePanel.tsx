import type { OneReport } from "../api";

export function ScorePanel({ report }: { report: OneReport }) {
  const { score, raw, vs_reference } = report;
  const verdict = verdictFor(score.composite);

  return (
    <div className="rounded-2xl border border-kt-edge bg-kt-panel p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">Dexterity report</h2>
        <span className={`text-sm font-bold ${verdict.tone}`}>{verdict.label}</span>
      </div>

      {/* ── Metric cards with descriptions + raw values ── */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <MetricCard
          label="Speed"
          value={score.speed}
          desc="Wrist travel speed"
          detail={`avg ${raw.mean_speed?.toFixed(4) ?? "—"} u/s`}
        />
        <MetricCard
          label="Accuracy"
          value={score.accuracy}
          desc="Path directness"
          detail={`straightness ${(raw.straightness ?? 0).toFixed(3)}`}
        />
        <MetricCard
          label="Quality"
          value={score.quality}
          desc="Movement smoothness"
          detail={`jerk ${formatJerk(raw.dimensionless_jerk)}`}
        />
      </div>

      {/* ── Composite ── */}
      <div className="mt-4 rounded-xl border border-kt-edge bg-black/30 p-4">
        <div className="flex items-end justify-between">
          <span className="text-xs uppercase tracking-wider text-kt-muted">
            Composite dexterity
          </span>
          <span className="font-mono text-3xl font-bold text-kt-cyan">
            {score.composite.toFixed(0)}
            <span className="text-base text-kt-muted">/100</span>
          </span>
        </div>
        <Bar value={score.composite} />
      </div>

      {/* ── Vs reference ── */}
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <Stat
          label="Speed vs normal"
          value={`${(vs_reference.speed_ratio * 100).toFixed(0)}%`}
          hint={
            vs_reference.slower_than_normal_pct > 0
              ? `${vs_reference.slower_than_normal_pct.toFixed(0)}% slower`
              : "at/above normal"
          }
        />
        <Stat
          label="Smoothness vs normal"
          value={`${(vs_reference.smoother_ratio * 100).toFixed(0)}%`}
          hint="higher = smoother"
        />
      </div>

      {/* ── Measurement Method (explains what/how/where) ── */}
      <div className="mt-4 rounded-xl border border-kt-edge bg-black/20 p-4">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-kt-cyan">
          How we measure
        </div>
        <div className="mt-2 space-y-1.5 text-xs leading-relaxed text-kt-muted">
          <p>
            <span className="text-kt-ink font-semibold">Tracking:</span> MediaPipe
            AI detects 21 landmarks on the hand per video frame (wrist, finger
            joints, fingertips).
          </p>
          <p>
            <span className="text-kt-ink font-semibold">Speed</span> — average
            velocity of the wrist (landmark 0) across the reach-grasp-lift
            cycle. Higher = faster.
          </p>
          <p>
            <span className="text-kt-ink font-semibold">Accuracy</span> — net
            displacement ÷ total path length of the wrist. 1.0 = perfectly
            straight reach. Lower = more meandering / corrective sub-movements.
          </p>
          <p>
            <span className="text-kt-ink font-semibold">Quality</span> — inverse
            of mean-squared jerk (3rd derivative of position). Smooth movements
            have low jerk; impaired movements fragment into jerky sub-movements.
          </p>
          <p>
            <span className="text-kt-ink font-semibold">Reference:</span>{" "}
            normalised against an embedded normal-hand baseline (real hand
            video, 2D image landmarks, ×1.5 soft margin).
          </p>
          <p>
            <span className="text-kt-ink font-semibold">Learned Non-Use:</span>{" "}
            a clearly lower composite on one side indicates the hand the patient
            has &quot;forgotten&quot; to use.
          </p>
        </div>
      </div>

      {/* ── Raw data (for transparency) ── */}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-kt-cyan hover:underline">
          Raw measurement data
        </summary>
        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-black/20 p-3 font-mono text-xs text-kt-muted">
          <span>mean_speed: {raw.mean_speed?.toFixed(6)}</span>
          <span>straightness: {raw.straightness?.toFixed(6)}</span>
          <span>dim_jerk: {formatJerk(raw.dimensionless_jerk)}</span>
          <span>velocity_peaks: {raw.velocity_peaks}</span>
          <span>smoothness_idx: {raw.smoothness_index?.toFixed(4)}</span>
          <span>tracking: {raw.velocity_peaks > 50 ? "partial" : "good"}</span>
        </div>
      </details>
    </div>
  );
}

function MetricCard({
  label,
  value,
  desc,
  detail,
}: {
  label: string;
  value: number;
  desc: string;
  detail: string;
}) {
  return (
    <div className="rounded-xl border border-kt-edge bg-black/20 p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-kt-muted">
        {label}
      </div>
      <div className="text-[10px] text-kt-muted/70">{desc}</div>
      <div className="mt-1 font-mono text-2xl font-semibold">{value.toFixed(0)}</div>
      <Bar value={value} />
      <div className="mt-1 font-mono text-[10px] text-kt-muted/60">{detail}</div>
    </div>
  );
}

function Bar({ value }: { value: number }) {
  const v = Math.max(0, Math.min(100, value));
  const color = v >= 80 ? "bg-kt-green" : v >= 55 ? "bg-kt-amber" : "bg-kt-red";
  return (
    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-kt-edge">
      <div className={`h-full ${color}`} style={{ width: `${v}%` }} />
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-kt-edge bg-black/20 p-3">
      <div className="text-[11px] uppercase tracking-wider text-kt-muted">{label}</div>
      <div className="mt-1 font-mono text-lg font-semibold">{value}</div>
      <div className="text-[11px] text-kt-muted">{hint}</div>
    </div>
  );
}

function formatJerk(v: number | undefined): string {
  if (!v || !isFinite(v)) return "—";
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(1);
}

function verdictFor(composite: number): { label: string; tone: string } {
  if (composite >= 85) return { label: "● Normal range", tone: "text-kt-green" };
  if (composite >= 60) return { label: "● Mild impairment", tone: "text-kt-amber" };
  return { label: "● Significant impairment", tone: "text-kt-red" };
}
