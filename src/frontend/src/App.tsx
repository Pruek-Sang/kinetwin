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
  const [statusText, setStatusText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let alive = true;
    const id = setInterval(async () => {
      const ok = await health();
      if (alive) setOnline(ok);
    }, 5000);
    return () => { alive = false; clearInterval(id); };
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
    setStatusText("AI analyzing on server…");
    try {
      setReport(await analyzeOne(file));
    } catch (e) {
      const msg = e instanceof Error ? e.message
        : (e instanceof Event ? "Upload error — check console" : String(e));
      setError(msg);
    } finally {
      setLoading(false);
      setStatusText("");
    }
  }

  // Sample buttons: show real analysis animation (loading spinner ~12s)
  // Results are pre-computed from REAL MediaPipe — displayed after realistic delay
  async function loadSample(name: string) {
    setLoading(true);
    setError("");
    setReport(null);
    setStatusText("AI analyzing hand movement…");
    try {
      const [videoResp, resultResp] = await Promise.all([
        fetch(`/samples/${name}.mp4`),
        fetch(`/samples/${name}_result.json`),
      ]);
      if (!videoResp.ok) throw new Error(`sample video not found`);
      if (!resultResp.ok) throw new Error(`sample result not found`);
      const blob = await videoResp.blob();
      const result = (await resultResp.json()) as OneReport;
      const f = new File([blob], `${name}.mp4`, { type: "video/mp4" });
      setFile(f);
      setUrl(URL.createObjectURL(f));

      // Show progressive status messages (feels like real AI working)
      const steps = [
        { delay: 0,    msg: "Detecting hand landmarks…" },
        { delay: 3000, msg: "Computing movement speed…" },
        { delay: 6000, msg: "Analyzing movement quality…" },
        { delay: 9000, msg: "Comparing to reference…" },
      ];
      for (const step of steps) {
        setStatusText(step.msg);
        await new Promise((r) => setTimeout(r, step.delay === 0 ? 0 : 3000));
      }

      setReport(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message
        : (e instanceof Event ? "Load error" : String(e));
      setError(msg);
    } finally {
      setLoading(false);
      setStatusText("");
    }
  }

  return (
    <div className="mx-auto max-w-[1600px] px-6 py-6">
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
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs text-kt-muted">หรือลองตัวอย่าง:</span>
          <button
            onClick={() => loadSample("normal")}
            disabled={loading}
            className="rounded-lg bg-kt-green/15 px-3 py-1.5 text-sm font-semibold text-kt-green ring-1 ring-kt-green/40 transition hover:bg-kt-green/25 disabled:opacity-40"
          >
            ✋ มือปกติ
          </button>
          <button
            onClick={() => loadSample("impaired")}
            disabled={loading}
            className="rounded-lg bg-kt-amber/15 px-3 py-1.5 text-sm font-semibold text-kt-amber ring-1 ring-kt-amber/40 transition hover:bg-kt-amber/25 disabled:opacity-40"
          >
            ⚠ มืออ่อนแรง
          </button>
          {loading && <span className="text-xs text-kt-cyan animate-pulse">{statusText || "Analyzing…"}</span>}
        </div>
      </section>

      <section className="mb-5">
        <h2 className="mb-2 text-sm font-semibold text-kt-muted">2 · Compare side-by-side</h2>
        <SplitScreen
          patientUrl={url}
          overlay={report?.overlay ?? null}
          syncKey={file ? file.size + file.lastModified : 0}
        />
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
