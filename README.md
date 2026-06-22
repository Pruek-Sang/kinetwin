# KineTwin — Kinematic Digital Twin

Detecting **Learned Non-Use** in elderly hand movement through video.

> Hackathon project — *Digital Aiding 4 Aging Hackathon 2026* (AI Vibe Coding track).
> Problem statement in [`doc/`](doc).

## What it does

A patient performs a single **Reach → Grasp → Lift** task (lift a cup). KineTwin
analyses the video and reports the three metrics the brief asks for —
**Speed, Accuracy, Quality of movement** — then compares the hand against an
embedded *normal reference* (a kinematic 21-landmark skeleton) to flag a
suspected **Learned Non-Use** side (the hand the patient has "forgotten" how to
use).

The reference on the right of the split-screen is a **kinematic skeleton**
driven by the same 21-landmark schema the metrics use, so the comparison is
mathematically consistent.

## Architecture (layered, one focused case)

```
src/
  ai/         MediaPipe tracking + pure-Python metrics (Speed/Accuracy/Quality)
              └─ tracking/data/reference_hand_trajectory.json  (the Blender export)
  backend/    FastAPI, stateless: POST /analyze, /analyze-one, /analyze-landmarks
  frontend/   React + Vite + TS, split-screen patient|reference + score panel
  deploy/     Blender scripts that build/rig/animate/export the reference
doc/          problem statement
tests/        cross-layer tests (metrics, tracking, backend API)
```

No DB, no auth, no session — a stateless analysis tool.

## Status

| # | Layer | Status |
|---|---|---|
| ① | `src/ai/metrics` — Speed / Accuracy / Quality + scorer | ✅ done (unit-tested) |
| ② | `src/ai/tracking` — MediaPipe → landmarks + pipeline | ✅ done (tested) |
| ③ | `src/backend` — FastAPI `POST /analyze*` | ✅ done (TestClient tests) |
| ④ | Blender kinematic-skeleton reference (21-landmark export) | ✅ done (interim; a nicer hand model can be dropped in later) |
| ⑤ | `src/frontend` — split-screen + score UI | ✅ done (builds) |
| ⑥ | Deploy — Docker (`kinetwin-*`) + GitHub Pages + README | ✅ done |

Full suite: **27 tests passing** (16 metrics + 7 tracking + 4 backend).

## Run locally

### Backend (FastAPI)
```powershell
python -m pip install -r src\backend\requirements.txt
# from src/backend:
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Frontend (Vite)
```powershell
cd src\frontend
npm install
npm run dev     # http://localhost:5173  (proxies /analyze* to :8000)
```
Open the app, upload a patient task video, press **Analyze**.

### One-shot full stack (Docker, isolated `kinetwin-*` names)
```powershell
docker compose up --build
# frontend: http://localhost:5173   backend: http://localhost:8000
```

## Deploy

* **Frontend** → GitHub Pages (workflow in `.github/workflows/pages.yml`).
  Set `KT_API_URL` repo secret to point at the backend if it is hosted
  elsewhere; leave blank for same-origin.
* **Backend** → the `kinetwin-backend` Docker image on any container host
  (Render / Railway / Cloud Run). No shared cloud resources — fully isolated.

## Reference hand (asset)

The interim reference is a procedural kinematic skeleton (`src/deploy/blender/`)
exporting the 21 MediaPipe landmarks. A higher-fidelity rigged hand can replace
it later without touching the metrics or API — the contract is the
`(T, 21, 3)` trajectory JSON.

## Run the tests
```powershell
python -m pip install -r src\ai\requirements.txt pytest
python -m pytest
```
