"""Backend API tests (in-process via FastAPI TestClient, no server needed)."""
from __future__ import annotations

import sys
from pathlib import Path

# make src/backend (for `app`) and src (for `ai`) importable
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parents[1] / "src"
for p in (str(_SRC / "backend"), str(_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from ai.tests.conftest import impaired_trajectory, normal_trajectory  # noqa: E402

client = TestClient(app)


def test_health_ok_and_reference_loaded():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["reference_baseline"] == "loaded"


def test_root():
    assert client.get("/").status_code == 200


def test_analyze_landmarks_flags_learned_non_use():
    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    payload = {
        "fps": 30.0,
        "left": impaired.landmarks.tolist(),
        "right": normal.landmarks.tolist(),
    }
    r = client.post("/analyze-landmarks", json=payload)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["dominant_hand"] == "right"
    assert rep["learned_non_use"]["flag"] is True
    assert rep["learned_non_use"]["hand"] == "left"
    assert rep["metrics"]["right"]["composite"] > rep["metrics"]["left"]["composite"]


def test_analyze_landmarks_rejects_too_few_frames():
    one = [[[0.0, 0.0, 0.0]] * 21]
    r = client.post("/analyze-landmarks", json={"fps": 30.0, "left": one, "right": one})
    assert r.status_code == 400
