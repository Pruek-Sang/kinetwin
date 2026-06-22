import { useEffect, useRef, useState } from "react";
import { analyzeOne, health, type OneReport } from "./api";
import { SplitScreen } from "./components/SplitScreen";
import { ScorePanel } from "./components/ScorePanel";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [report, setReport] = useState<OneReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let alive = true;
    const id = setInterval(async () => {
      const ok = await health();
      if (alive) setOnline(ok);
    }, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  function onFile(f: File | null) {
    if (!f) return;
    setFile(f);
    setUrl(URL.createObjectURL(f));
    setReport(null);
    setError("");
  }

  async function onAnalyze() {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      setReport(await analyzeOne(file));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Kine<span className="text-kt-cyan">Twin</span>
          </h1>
          <p className="text-sm text-kt-muted">
            Kinematic Digital Twin · detecting <span className="text-kt-ink">Learned Non-Use</span> from a
            reach-grasp-lift task video
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
            online
              ? "bg-kt-green/10 text-kt-green ring-kt-green/40"
              : "bg-kt-red/10 text-kt-red ring-kt-red/40"
          }`}
        >
          {online ? "API online" : "API offline"}
        </span>
      </header>

      <section className="mb-5 rounded-2xl border border-kt-edge bg-kt-panel p-5">
        <label className="block text-sm font-semibold">1 · Patient task video</label>
        <p className="mt-1 text-xs text-kt-muted">
          One continuous clip of the patient lifting the cup with the hand under assessment.
        </p>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={() => inputRef.current?.click()}
            className="rounded-lg bg-white/5 px-4 py-2 text-sm font-semibold ring-1 ring-kt-edge hover:bg-white/10"
          >
            Choose video…
          </button>
          <span className="truncate text-sm text-kt-muted">
            {file ? file.name : "no file selected"}
          </span>
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => onFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </section>

      <section className="mb-5">
        <h2 className="mb-2 text-sm font-semibold text-kt-muted">2 · Compare side-by-side</h2>
        <SplitScreen patientUrl={url} syncKey={file ? file.size + file.lastModified : 0} />
      </section>

      <section className="mb-5 flex items-center gap-3">
        <button
          onClick={onAnalyze}
          disabled={!file || loading}
          className="rounded-xl bg-kt-cyan px-6 py-2.5 text-sm font-bold text-black transition hover:brightness-110 disabled:opacity-40"
        >
          {loading ? "Analyzing…" : "3 · Analyze movement"}
        </button>
        {error && <span className="text-sm text-kt-red">⚠ {error}</span>}
      </section>

      {report && <ScorePanel report={report} />}

      <footer className="mt-10 border-t border-kt-edge pt-4 text-xs text-kt-muted">
        KineTwin · Reach-Grasp-Lift · Speed / Accuracy / Quality scoring + Learned Non-Use flag.
      </footer>
    </div>
  );
}
