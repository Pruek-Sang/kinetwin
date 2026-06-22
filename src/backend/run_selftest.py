"""Self-test for the KineTwin backend using FastAPI's TestClient.

Hits /health and /analyze-landmarks with synthetic normal vs impaired landmark
trajectories (no real video, no running server). Run from src/backend:

    python run_selftest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# make src/backend and src importable
HERE = Path(__file__).resolve().parent
SRC = HERE.parent
for p in (str(HERE), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from ai.tests.conftest import impaired_trajectory, normal_trajectory  # noqa: E402


def main() -> None:
    client = TestClient(app)

    health = client.get("/health").json()
    print("HEALTH:", health)

    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    payload = {
        "fps": 30.0,
        "left": impaired.landmarks.tolist(),
        "right": normal.landmarks.tolist(),
    }
    resp = client.post("/analyze-landmarks", json=payload)
    print("STATUS:", resp.status_code)
    report = resp.json()
    print("dominant_hand :", report["dominant_hand"])
    print("score_gap     :", report["score_gap"])
    print("learned_non_use:", report["learned_non_use"])
    for side in ("left", "right"):
        m = report["metrics"][side]
        print(f"  {side}: speed={m['speed']:.1f} acc={m['accuracy']:.1f} qual={m['quality']:.1f} composite={m['composite']:.1f}")

    assert resp.status_code == 200, resp.text
    assert report["dominant_hand"] == "right"
    assert report["learned_non_use"]["flag"] is True
    print("\nSELFTEST PASS")


if __name__ == "__main__":
    main()
