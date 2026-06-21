# KineTwin — Kinematic Digital Twin

Detecting **Learned Non-Use** in elderly hand movement through video.

> Hackathon project — *Digital Aiding 4 Aging Hackathon 2026* (AI Vibe Coding track).
> See [`doc/`](doc) for the full problem statement.

## What it does

A patient performs a single **Reach → Grasp → Lift** task (lift a cup) with each
hand. KineTwin analyses the two videos and reports the three metrics the brief
asks for — **Speed, Accuracy, Quality of movement** — then compares the two
hands to flag a suspected **Learned Non-Use** side (the hand the patient has
"forgotten" how to use).

The "correct example" shown on the right of the split-screen is a **3D Blender
reference hand** driven by the same 21-landmark schema, so the patient video and
the ideal reference are scored by the *same* math.

## Architecture (layered, one focused case)

```
src/
  ai/         MediaPipe tracking + pure-Python metrics (Speed/Accuracy/Quality)
  backend/    FastAPI, one stateless endpoint: POST /analyze
  frontend/   React + Vite + TS, split-screen patient|reference + score overlay
  deploy/     Docker, GitHub Pages workflow (isolated, no shared cloud resources)
doc/          problem statement, reference material
tests/        cross-layer integration tests
```

## Layers status

| # | Layer | Status |
|---|---|---|
| ① | `src/ai/metrics` — Speed/Accuracy/Quality + scorer | done (unit-tested) |
| ② | `src/ai/tracking` — MediaPipe video → landmarks | planned |
| ③ | `src/backend` — FastAPI `POST /analyze` | planned |
| ④ | Blender 3D reference hand | in progress |
| ⑤ | `src/frontend` — split-screen UI | planned |
| ⑥ | `src/deploy` — GitHub + Docker | planned |

## Run the metrics tests

```powershell
python -m pip install -r src\ai\requirements.txt pytest
python -m pytest
```

> Uses the system Python at
> `C:\Users\Welcome\AppData\Local\Programs\Python\Python311\python.exe`.
