"""KineTwin FastAPI app.

Two analysis entry points (stateless, no DB / auth / session):

* ``POST /analyze``            -- multipart upload of two task videos
  (``left_video`` + ``right_video``); runs MediaPipe tracking then the metrics.
* ``POST /analyze-landmarks``  -- JSON of two pre-tracked landmark arrays +
  ``fps``; skips video processing (handy for tests / the demo).

Plus ``GET /health`` and ``GET /``. CORS is open (frontend is served
separately). The only middleware is a request-size guard.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

# Make the ai package (../../ai) importable when running from src/backend.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .schemas import AnalyzeReport, HandMetrics
from .services import (
    analyze_landmark_json,
    analyze_one_landmarks,
    analyze_one_video,
    analyze_two_videos,
    get_reference_baseline,
)

MAX_VIDEO_BYTES = 80 * 1024 * 1024  # 80 MB per upload -- guard, not strict middleware

app = FastAPI(
    title="KineTwin API",
    description="Learned Non-Use detection from hand task videos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LandmarksRequest(BaseModel):
    fps: float = Field(30.0, gt=0)
    left: List[List[List[float]]]   # (T, 21, 3)
    right: List[List[List[float]]]  # (T, 21, 3)
    weights: Optional[dict] = None
    gap: Optional[float] = None


class OneLandmarksRequest(BaseModel):
    fps: float = Field(30.0, gt=0)
    landmarks: List[List[List[float]]]  # (T, 21, 3)


@app.get("/")
def root():
    return {"service": "KineTwin API", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    # touch the reference baseline so we know the asset is wired
    try:
        get_reference_baseline()
        ref = "loaded"
    except Exception as exc:  # pragma: no cover
        ref = f"error: {exc}"
    return {"status": "ok", "reference_baseline": ref}


@app.post("/analyze-landmarks", response_model=AnalyzeReport)
def analyze_landmarks(req: LandmarksRequest):
    if len(req.left) < 2 or len(req.right) < 2:
        raise HTTPException(status_code=400, detail="each hand needs >= 2 frames")
    kwargs = {}
    if req.weights:
        kwargs["weights"] = req.weights
    if req.gap is not None:
        kwargs["gap"] = req.gap
    report = analyze_landmark_json(req.left, req.right, req.fps, **kwargs)
    return _to_report(report)


@app.post("/analyze", response_model=AnalyzeReport)
async def analyze(
    left_video: UploadFile = File(...),
    right_video: UploadFile = File(...),
    fps: float = Form(0.0),
):
    data_l = await left_video.read()
    data_r = await right_video.read()
    if len(data_l) > MAX_VIDEO_BYTES or len(data_r) > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="video too large (max 80 MB each)")

    tmpdir = Path(tempfile.gettempdir())
    left_path = tmpdir / f"kt_left_{uuid.uuid4().hex}{Path(left_video.filename or '.mp4').suffix}"
    right_path = tmpdir / f"kt_right_{uuid.uuid4().hex}{Path(right_video.filename or '.mp4').suffix}"
    left_path.write_bytes(data_l)
    right_path.write_bytes(data_r)
    try:
        report = analyze_two_videos(str(left_path), str(right_path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"analysis failed: {exc}")
    finally:
        for p in (left_path, right_path):
            try:
                p.unlink()
            except OSError:
                pass
    return _to_report(report)


@app.post("/analyze-one-landmarks")
def analyze_one_landmarks_endpoint(req: OneLandmarksRequest):
    if len(req.landmarks) < 2:
        raise HTTPException(status_code=400, detail="need >= 2 frames")
    return analyze_one_landmarks(req.landmarks, req.fps)


@app.post("/analyze-one", response_model=dict)
async def analyze_one(video: UploadFile = File(...)):
    data = await video.read()
    if len(data) > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="video too large (max 80 MB)")
    tmpdir = Path(tempfile.gettempdir())
    path = tmpdir / f"kt_one_{uuid.uuid4().hex}{Path(video.filename or '.mp4').suffix}"
    path.write_bytes(data)
    try:
        return analyze_one_video(str(path))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"analysis failed: {exc}")
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def _to_report(report: dict) -> AnalyzeReport:
    metrics = {
        side: HandMetrics(
            speed=m["speed"], accuracy=m["accuracy"], quality=m["quality"],
            composite=m["composite"], raw=m["raw"],
        )
        for side, m in report["metrics"].items()
    }
    return AnalyzeReport(
        metrics=metrics,
        dominant_hand=report["dominant_hand"],
        score_gap=report["score_gap"],
        learned_non_use=report["learned_non_use"],
        weights=report.get("weights", {}),
        learned_non_use_gap_threshold=report.get("learned_non_use_gap_threshold", 0.0),
    )
