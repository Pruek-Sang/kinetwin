import type { OneReport } from "../api";

export function ScorePanel({ report }: { report: OneReport }) {
  const { score, vs_reference } = report;
  const verdict = verdictFor(score.composite);
  return (
    <div className="rounded-2xl border border-kt-edge bg-kt-panel p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">Dexterity report</h2>
        <span className={`text-sm font-bold ${verdict.tone}`}>{verdict.label}</span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <Metric label="Speed" value={score.speed} />
        <Metric label="Accuracy" value={score.accuracy} />
        <Metric label="Quality" value={score.quality} />
      </div>

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

      <p className="mt-4 text-xs leading-relaxed text-kt-muted">
        Scores are normalised against the embedded reference. A clearly lower
        composite on one side is the signature of{" "}
        <span className="text-kt-ink">Learned Non-Use</span>.
      </p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-kt-edge bg-black/20 p-3">
      <div className="text-[11px] uppercase tracking-wider text-kt-muted">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold">{value.toFixed(0)}</div>
      <Bar value={value} />
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

function verdictFor(composite: number): { label: string; tone: string } {
  if (composite >= 85) return { label: "● Normal range", tone: "text-kt-green" };
  if (composite >= 60) return { label: "● Mild impairment", tone: "text-kt-amber" };
  return { label: "● Significant impairment", tone: "text-kt-red" };
}
