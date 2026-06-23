"""Validate a real hand video LOCALLY: run MediaPipe, draw the 21-landmark
skeleton onto every frame -> an annotated MP4 you can watch to judge whether
tracking is correct (Cipher can read the numbers but cannot see the video, so a
human reviews the annotated output).

Nothing is uploaded -- it runs entirely on your machine (safe for patient data).

Usage:
    python src\\ai\\validate_video.py <video_path> [annotated_out.mp4]

It prints: frames detected / total, tracking %, and Speed/Accuracy/Quality.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# make `ai` importable when run from the repo root
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import cv2  # noqa: E402
import mediapipe as mp  # noqa: E402
import numpy as np  # noqa: E402
from mediapipe.tasks import python as mp_tasks  # noqa: E402
from mediapipe.tasks.python import vision  # noqa: E402

from ai.metrics import raw_metrics, score_hand, ReferenceBaseline  # noqa: E402
from ai.metrics.trajectory import HandTrajectory  # noqa: E402
from ai.tracking.hand_tracker import MODEL_PATH  # noqa: E402
from ai.tracking.reference import load_reference_trajectory  # noqa: E402

# MediaPipe HAND_CONNECTIONS for drawing
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def validate(video_path: str, out_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(video_path)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)

    options = vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    world_frames = []  # (21,3) per detected frame, for the metrics
    total = 0
    detected = 0

    cyan = (208, 211, 34)  # BGR ~ #22d3ee
    white = (246, 237, 230)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        total += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts_ms = int(round(total * 1000.0 / fps))
        result = landmarker.detect_for_video(mp_image, ts_ms)

        if result.hand_landmarks:
            detected += 1
            hl = result.hand_landmarks[0]
            pts = [(int(p.x * w), int(p.y * h)) for p in hl]
            for a, b in CONNECTIONS:
                cv2.line(frame, pts[a], pts[b], cyan, 3, cv2.LINE_AA)
            for p in pts:
                cv2.circle(frame, p, 5, white, -1, cv2.LINE_AA)
            wl = result.hand_world_landmarks[0]
            world_frames.append([[lm.x, lm.y, lm.z] for lm in wl])
        else:
            cv2.putText(frame, "no hand", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 0, 255), 2)
        writer.write(frame)

    cap.release()
    writer.release()
    landmarker.close()

    # metrics on the detected frames (if any)
    metrics = {}
    if len(world_frames) >= 2:
        traj = HandTrajectory(landmarks=np.asarray(world_frames, dtype=float),
                              fps=fps, label="patient")
        bl = ReferenceBaseline.from_trajectory(load_reference_trajectory())
        metrics = {**raw_metrics(traj), **{k: v for k, v in score_hand(traj, bl).__dict__.items() if isinstance(v, (int, float))}}

    return {
        "video": video_path,
        "annotated": out_path,
        "frames_total": total,
        "frames_with_hand": detected,
        "tracking_pct": round(100.0 * detected / total, 1) if total else 0.0,
        "fps": round(fps, 2),
        "metrics": metrics,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python validate_video.py <video> [out.mp4]")
        sys.exit(1)
    vpath = sys.argv[1]
    opath = sys.argv[2] if len(sys.argv) > 2 else str(
        Path(vpath).with_name(Path(vpath).stem + "_annotated.mp4"))
    res = validate(vpath, opath)
    print("=== VALIDATE ===")
    print("video          :", res["video"])
    print("annotated (WATCH THIS) :", res["annotated"])
    print(f"frames: {res['frames_with_hand']}/{res['frames_total']}  "
          f"({res['tracking_pct']}% tracked)  fps={res['fps']}")
    if res["metrics"]:
        m = res["metrics"]
        print("Speed=%.1f  Acc=%.1f  Qual=%.1f  composite=%.1f" % (
            m.get("speed", 0), m.get("accuracy", 0), m.get("quality", 0), m.get("composite", 0)))
    else:
        print("not enough hand detections to score (<2 frames)")
