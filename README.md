<div align="center">

# 🖐️ KineTwin

### Kinematic Digital Twin — AI-Powered Learned Non-Use Detection

*Detect which hand your patient has "forgotten" to use — from a single phone video.*

</div>

---

## 🎯 What It Does

KineTwin analyzes a **Reach → Grasp → Lift** task (lifting a cup) from ordinary video and reports whether a patient shows signs of **Learned Non-Use** — the neurological phenomenon where stroke survivors and elderly patients progressively stop using their weaker hand until the brain "forgets" how.

| Metric | What It Measures | How |
|---|---|---|
| **⚡ Speed** | Wrist travel velocity | Average speed of wrist landmark across the task |
| **🎯 Accuracy** | Path directness | Net displacement ÷ total path length (1.0 = perfectly straight) |
| **🌊 Quality** | Movement smoothness | Inverse of mean-squared jerk (3rd derivative of position) |
| **🔴 Stability Map** | Per-joint tremor detection | 21 landmarks colour-coded: 🟢 stable / 🟡 borderline / 🔴 unstable |

> **Learned Non-Use flag:** If one hand scores significantly lower than the other, the system flags it as a suspected "forgotten" hand — the signature of Learned Non-Use.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER (React)                      │
│                                                          │
│  📹 Video plays → 🤖 AI overlay tracks hand in real-time │
│  21 landmarks per frame × colour-coded stability map     │
│  Split-screen: patient (left) vs reference (right)       │
│                                                          │
│  AI: MediaPipe Hands (deep learning perception)           │
└──────────────────────┬──────────────────────────────────┘
                       │ landmarks JSON (~50KB)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                BACKEND (FastAPI / Cloud Run)              │
│                                                          │
│  AI: Scikit-learn classifier predicts LNU (planned)      │
│  Speed / Accuracy / Quality scoring (pure math)          │
│  Reference: real normal-hand baseline                   │
└─────────────────────────────────────────────────────────┘
```

**AI Layer:**
- **MediaPipe Hands** (Google's deep-learning model) detects 21 hand landmarks from video — this is the AI perception engine
- Movement metrics (Speed/Accuracy/Quality) use **pure kinematic math** — transparent, auditable, no black box
- Backend serves real-time analysis via Cloud Run (stateless)

---

## 🧠 How It Works

```
Video → MediaPipe 21 landmarks/frame
      → Wrist trajectory (landmark 0)
      → Speed = avg velocity
      → Accuracy = path straightness ratio
      → Quality = dimensionless jerk (smoothness)
      → Per-landmark stability = frame-to-frame jitter vs reference
      → Colour map: 🟢 normal / 🟡 borderline / 🔴 impaired
      → Classifier: normal vs Learned Non-Use (heuristic threshold, ML classifier planned)
```

**Reference baseline:** A real normal-hand video sets the standard. Patient landmarks are compared per-joint — stable joints stay green, tremoring joints turn red. This pinpoints *where* the weakness is, not just *whether* it exists.

---

## 🚀 Quick Start

### Run locally
```bash
# Backend
cd src/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd src/frontend
npm install
npm run dev    # → http://localhost:5173
```

### Docker (one command)
```bash
docker compose up --build
# frontend: http://localhost:5173
# backend:  http://localhost:8000
```

### Try it
1. Open the web app
2. Click **"✋ มือปกติ"** (normal hand) — see all-green tracking + high scores
3. Click **"⚠ มืออ่อนแรง"** (impaired hand) — see red/amber joints + lower scores
4. Or upload your own video for real analysis

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Hand tracking | **MediaPipe Hands** (on-device deep learning) |
| Metrics | **NumPy** — kinematic math (dimensionless jerk, path straightness) |
| Backend | **FastAPI** (Python, stateless) |
| Frontend | **React + Vite + TypeScript + Tailwind CSS** |
| 3D Reference | **Three.js** (renders Blender hand model in-browser) |
| Deploy | **Google Cloud Run** (separate frontend/backend services) |
| CI/CD | **GitHub Actions** (test → build → deploy automatically) |
| Tests | **pytest** (27 passing) |

---

## 📁 Project Structure

```
KineTwin/
├── src/
│   ├── ai/                  # Metrics engine + MediaPipe tracker
│   │   ├── metrics/         # Speed / Accuracy / Quality (pure Python)
│   │   ├── tracking/        # MediaPipe wrapper + reference data
│   │   └── tests/           # 16 unit tests
│   ├── backend/             # FastAPI (stateless, 4 endpoints)
│   ├── frontend/            # React app (split-screen + overlay + scores)
│   │   └── public/samples/  # Sample videos + pre-computed results
│   └── deploy/
│       ├── blender/         # Blender reference hand scripts
│       └── cloudrun/        # Docker + Cloud Build configs
├── tests/                   # Cross-layer tests (backend API)
├── doc/                     # Problem statement + pitch
├── Plan/                    # Roadmap + Tech debt
├── Dockerfile.backend       # Backend container
├── docker-compose.yml       # Full-stack local
└── .github/workflows/       # CI/CD pipeline
```

---

## 🧪 Testing

```bash
python -m pytest      # 27 tests (metrics + tracking + API)
```

Coverage:
- Speed / Accuracy / Quality formulas (unit-tested with synthetic trajectories)
- Pipeline: video → landmarks → report
- Backend API: health, landmark analysis, video upload (no crash)

---

## 🔗 Live Demo

- **Frontend:** [kinetwin-frontend-rc5mtgajza-as.a.run.app](https://kinetwin-frontend-rc5mtgajza-as.a.run.app)
- **API Docs:** [kinetwin-backend-rc5mtgajza-as.a.run.app/docs](https://kinetwin-backend-rc5mtgajza-as.a.run.app/docs)

---

## 📊 Judging Criteria

| Criterion | Points | How KineTwin Scores |
|---|---|---|
| **Problem & Impact** | 30 | Directly addresses Learned Non-Use screening — accessible from any phone |
| **Prototype & Tech** | 30 | Working end-to-end: MediaPipe + FastAPI + React + Cloud Run |
| **Creativity** | 25 | Kinematic Digital Twin + per-joint stability colour map |
| **Pitching** | 15 | Live demo with split-screen comparison + progressive AI analysis |

---

## 📄 License

This project is licensed under **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial) — see [LICENSE](LICENSE).

```
✅ You CAN use, modify, and share this project
❌ You CANNOT sell it or use it commercially
✅ You MUST credit "KineTwin" if you use or adapt it
```

> **Why CC BY-NC?** This is a healthcare research project built for a hackathon.
> We want people to learn from and build on it — but not profit from it directly.
> Full license: https://creativecommons.org/licenses/by-nc/4.0/

> **Third-party assets:** The hand reference model is licensed under CC BY 4.0 — see [LICENSE-ASSETS.md](LICENSE-ASSETS.md).

---

## 🏆 Acknowledgements

- **MediaPipe** by Google — hand landmark detection
- **Scikit-learn** — ML classifier
- **FastAPI + React + Three.js** — open-source stack
- Built for **Digital Aiding 4 Aging Hackathon 2026** (AI Vibe Coding track)

---

<div align="center">

**[🌐 Live Demo](https://kinetwin-frontend-rc5mtgajza-as.a.run.app)** ·
**[📦 GitHub](https://github.com/Pruek-Sang/kinetwin)** ·
**[📖 Docs](https://github.com/Pruek-Sang/kinetwin/blob/main/doc/PROJECT_DESCRIPTION.md)**

*Built with ❤️ for elderly care · Powered by AI, not cloud bills*

</div>
