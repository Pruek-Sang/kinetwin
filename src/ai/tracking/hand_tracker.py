"""MediaPipe Hands video tracker (MediaPipe Tasks API).

mediapipe >= 0.10.14 removed the legacy ``mp.solutions.hands`` API, so this
uses the current **Tasks API** (``HandLandmarker`` with the
``hand_landmarker.task`` model). The model is bundled at
``models/hand_landmarker.task``.

One pass over the video captures, per frame, every detected hand's:
  * ``handedness`` ("Left"/"Right"),
  * **world** landmarks (relative-metric 3D, for the metrics), and
  * **image** landmarks (normalised x,y in [0,1], for the canvas overlay).

So ``analyze-one`` runs the detector exactly once and derives both the
trajectory and the overlay from the same pass.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from ..metrics.trajectory import HandTrajectory

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "hand_landmarker.task")


@dataclass(frozen=True)
class FrameDetection:
    """All hands detected in one video frame.

    Each hand is ``(handedness, world(21,3), image(21,2))``.
    """

    frame_index: int
    hands: tuple[tuple[str, np.ndarray, np.ndarray], ...]


@dataclass(frozen=True)
class TrackedHand:
    handedness: str
    trajectory: HandTrajectory

    @property
    def label(self) -> str:
        return self.trajectory.label


# ----------------------------------------------------------------- pure logic
def samples_to_trajectories(
    fps: float,
    detections,
    min_frames: int = 2,
) -> list[TrackedHand]:
    """Group per-frame detections by handedness into one trajectory per hand.

    Uses the WORLD landmarks (3D) for the metrics; the image landmarks are
    ignored here (consumed by :func:`samples_to_overlay`).
    """
    grouped: dict[str, list[np.ndarray]] = {}
    for det in detections:
        for handedness, _world, image in det.hands:
            # Use IMAGE landmarks (normalised x,y) instead of world (3D x,y,z)
            # because MediaPipe's z (monocular depth) is extremely noisy and
            # explodes jerk (3rd derivative). z=0 padding keeps the (21,3) shape.
            img = np.asarray(image, dtype=float)          # (21, 2)
            img3 = np.column_stack([img, np.zeros(img.shape[0])])  # (21, 3)
            grouped.setdefault(handedness, []).append(img3)

    tracked: list[TrackedHand] = []
    for handedness, samples in grouped.items():
        if len(samples) < min_frames:
            continue
        arr = np.stack(samples, axis=0)  # (T, 21, 3)
        try:
            traj = HandTrajectory(landmarks=arr, fps=fps, label=handedness.lower())
        except ValueError:
            continue
        tracked.append(TrackedHand(handedness=handedness, trajectory=traj))
    return tracked


def samples_to_overlay(detections) -> list:
    """Per-frame IMAGE landmarks (21 [x,y] in [0,1]) of the first detected hand,
    or ``None`` when no hand was found. Used to draw the skeleton overlay.
    """
    out: list = []
    for det in detections:
        if det.hands:
            out.append(det.hands[0][2].tolist())
        else:
            out.append(None)
    return out


# --------------------------------------------------------------- mediapipe part
def _make_landmarker(max_hands: int, running_mode, min_detection: float,
                     min_presence: float, min_tracking: float):
    """Create a HandLandmarker (Tasks API). Lazy import."""
    from mediapipe.tasks import python as mp_tasks  # noqa: WPS433
    from mediapipe.tasks.python import vision  # noqa: WPS433

    options = vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=running_mode,
        num_hands=max_hands,
        min_hand_detection_confidence=min_detection,
        min_hand_presence_confidence=min_presence,
        min_tracking_confidence=min_tracking,
    )
    return vision.HandLandmarker.create_from_options(options)


def extract_hand_samples(
    video_path: str,
    max_num_hands: int = 2,
    min_detection_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
    progress: Optional[Callable[[int, int], None]] = None,
) -> tuple[float, list[FrameDetection]]:
    """Run the HandLandmarker over every frame of ``video_path`` (one pass).

    Returns ``(fps, detections)`` where each detection carries every hand's
    world + image landmarks + handedness. Needs the ``mediapipe`` package and
    the bundled ``hand_landmarker.task`` model.
    """
    import cv2  # noqa: WPS433
    import mediapipe as mp  # noqa: WPS433
    from mediapipe.tasks.python import vision  # noqa: WPS433

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    landmarker = _make_landmarker(
        max_num_hands, vision.RunningMode.VIDEO,
        min_detection_confidence, min_detection_confidence, min_tracking_confidence,
    )

    detections: list[FrameDetection] = []
    frame_index = 0
    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            ts_ms = int(round(frame_index * 1000.0 / fps))
            result = landmarker.detect_for_video(mp_image, ts_ms)

            worlds = result.hand_world_landmarks or []
            imgs = result.hand_landmarks or []
            cats = result.handedness or []

            hands: list[tuple[str, np.ndarray, np.ndarray]] = []
            for i, wl in enumerate(worlds):
                label = "?"
                if i < len(cats) and cats[i]:
                    label = cats[i][0].category_name
                world = np.array([[lm.x, lm.y, lm.z] for lm in wl], dtype=float)
                image = None
                if i < len(imgs):
                    image = np.array([[lm.x, lm.y] for lm in imgs[i]], dtype=float)
                if image is not None:
                    hands.append((label, world, image))

            detections.append(FrameDetection(frame_index=frame_index, hands=tuple(hands)))
            frame_index += 1
            if progress is not None and total:
                progress(frame_index, total)
    finally:
        landmarker.close()
        cap.release()

    return fps, detections


def track_video(video_path: str, **kwargs) -> list[TrackedHand]:
    """Video -> tracked hands (convenience)."""
    fps, detections = extract_hand_samples(video_path, **kwargs)
    return samples_to_trajectories(fps, detections)
