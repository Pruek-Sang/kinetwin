"""MediaPipe Hands video tracker.

Reads a video with OpenCV, runs MediaPipe Hands on every frame, and turns the
per-frame 3D landmark detections into :class:`~ai.metrics.HandTrajectory`
objects (one per detected hand). MediaPipe is imported *lazily* inside the
functions so that the rest of the AI layer (and its unit tests) does not pay the
import cost or require the dependency.

Two halves, kept separate for testability:

* :func:`extract_hand_samples` -- the thin MediaPipe/OpenCV part (needs a real
  video + the ``mediapipe``/``opencv-python`` packages).
* :func:`samples_to_trajectories` -- the pure-Python grouping/conversion part
  (no MediaPipe, fully unit-testable with synthetic detections).

Landmark source
---------------
We use MediaPipe ``world_landmarks`` (relative-metric 3D, depth relative to the
wrist) rather than the normalised image landmarks, because Speed/Quality
metrics need real 3D motion. The scale is *relative* (no absolute metric
calibration), so:

* dimensionless jerk (Quality) and path straightness (Accuracy) are
  scale-invariant and compare fairly;
* mean speed (Speed) is in the same relative units and compares fairly **within
  one recording setup** (same camera distance).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import numpy as np

from ..metrics import N_LANDMARKS
from ..metrics.trajectory import HandTrajectory


@dataclass(frozen=True)
class FrameDetection:
    """All hands detected in a single video frame."""

    frame_index: int
    hands: tuple[tuple[str, np.ndarray], ...]  # ((handedness, (21, 3)), ...)


@dataclass(frozen=True)
class TrackedHand:
    """One hand tracked across (a subsequence of) frames."""

    handedness: str
    trajectory: HandTrajectory

    @property
    def label(self) -> str:
        return self.trajectory.label


# ----------------------------------------------------------------- pure logic
def samples_to_trajectories(
    fps: float,
    detections: Iterable[FrameDetection],
    min_frames: int = 2,
) -> list[TrackedHand]:
    """Group per-frame detections by handedness into one trajectory per hand.

    Each hand is built from the subsequence of frames in which it was detected
    (assumed contiguous for a dedicated task video). Hands seen in fewer than
    ``min_frames`` frames are dropped.
    """
    grouped: dict[str, list[np.ndarray]] = {}
    for det in detections:
        for handedness, landmarks in det.hands:
            grouped.setdefault(handedness, []).append(np.asarray(landmarks, dtype=float))

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


# --------------------------------------------------------------- mediapipe part
def _new_hands_detector(max_num_hands: int, model_complexity: int,
                        min_detection_confidence: float,
                        min_tracking_confidence: float):
    """Create a MediaPipe Hands instance (lazy import)."""
    import mediapipe as mp  # noqa: WPS433 -- lazy import on purpose

    return mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=max_num_hands,
        model_complexity=model_complexity,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )


def extract_hand_samples(
    video_path: str,
    max_num_hands: int = 2,
    model_complexity: int = 1,
    min_detection_confidence: float = 0.6,
    min_tracking_confidence: float = 0.6,
    progress: Optional[Callable[[int, int], None]] = None,
) -> tuple[float, list[FrameDetection]]:
    """Run MediaPipe Hands over every frame of ``video_path``.

    Returns ``(fps, detections)`` where ``detections[t]`` is the
    :class:`FrameDetection` for frame ``t``. Frames with no hand still appear
    (with an empty ``hands`` tuple) so frame indices stay aligned with time.
    Needs ``mediapipe`` and ``opencv-python`` installed.
    """
    import cv2  # noqa: WPS433 -- lazy import on purpose

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        fps = 30.0  # fallback when the container has no fps metadata

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    detections: list[FrameDetection] = []
    frame_index = 0
    detector = _new_hands_detector(
        max_num_hands, model_complexity,
        min_detection_confidence, min_tracking_confidence,
    )
    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = detector.process(frame_rgb)

            hands: list[tuple[str, np.ndarray]] = []
            if results.multi_hand_world_landmarks and results.multi_handedness:
                for handedness, wl in zip(
                    results.multi_handedness, results.multi_hand_world_landmarks
                ):
                    label = handedness.classification[0].label  # "Left" / "Right"
                    arr = np.array(
                        [[lm.x, lm.y, lm.z] for lm in wl.landmark],
                        dtype=float,
                    )
                    hands.append((label, arr))
            detections.append(FrameDetection(frame_index=frame_index, hands=tuple(hands)))
            frame_index += 1
            if progress is not None and total:
                progress(frame_index, total)
    finally:
        detector.close()
        cap.release()

    return fps, detections


def track_video(video_path: str, **kwargs) -> list[TrackedHand]:
    """Full convenience pipeline: video -> list of tracked hands."""
    fps, detections = extract_hand_samples(video_path, **kwargs)
    return samples_to_trajectories(fps, detections)
