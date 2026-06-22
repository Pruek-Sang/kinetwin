"""Service layer: wraps the ai pipeline and the reference baseline.

The "normal" reference is the Blender-exported trajectory
(``reference_hand_trajectory.json``); patient videos are scored against it so the
numbers are absolute, not just relative to the patient's own two hands.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import numpy as np

from ai.metrics import (
    DEFAULT_LEARNED_NON_USE_GAP,
    DEFAULT_WEIGHTS,
    HandTrajectory,
    ReferenceBaseline,
    score_hand,
)
from ai.pipeline import analyze_trajectories, analyze_videos
from ai.tracking.reference import load_reference_trajectory


@lru_cache(maxsize=1)
def get_reference_baseline() -> ReferenceBaseline:
    """Load + cache the ideal reference baseline (from the Blender export)."""
    traj = load_reference_trajectory()
    return ReferenceBaseline.from_trajectory(traj)


def trajectories_from_landmarks(landmarks, fps: float, label: str) -> HandTrajectory:
    arr = np.asarray(landmarks, dtype=float)
    return HandTrajectory(landmarks=arr, fps=fps, label=label)


def analyze_landmark_json(
    left, right, fps: float,
    baseline: Optional[ReferenceBaseline] = None,
    weights: dict = DEFAULT_WEIGHTS,
    gap: float = DEFAULT_LEARNED_NON_USE_GAP,
) -> dict:
    bl = baseline or get_reference_baseline()
    left_t = trajectories_from_landmarks(left, fps, "left")
    right_t = trajectories_from_landmarks(right, fps, "right")
    return analyze_trajectories(left_t, right_t, baseline=bl, weights=weights, learned_non_use_gap=gap)


def analyze_two_videos(
    left_path: str, right_path: str,
    baseline: Optional[ReferenceBaseline] = None,
    weights: dict = DEFAULT_WEIGHTS,
    gap: float = DEFAULT_LEARNED_NON_USE_GAP,
) -> dict:
    bl = baseline or get_reference_baseline()
    return analyze_videos(left_path, right_path, baseline=bl, weights=weights, learned_non_use_gap=gap)


# --------------------------------------------------------------- single hand --
def _one_report(traj: HandTrajectory, baseline: ReferenceBaseline) -> dict:
    breakdown = score_hand(traj, baseline)
    raw = breakdown.raw
    ratio = raw["mean_speed"] / baseline.mean_speed if baseline.mean_speed > 0 else 0.0
    slower_pct = max(0.0, (1.0 - ratio)) * 100.0
    nc = raw["dimensionless_jerk"]
    bnc = baseline.dimensionless_jerk
    smoother_ratio = (bnc / nc) if (bnc > 0 and nc > 0) else 0.0
    return {
        "score": {
            "speed": round(breakdown.speed, 2),
            "accuracy": round(breakdown.accuracy, 2),
            "quality": round(breakdown.quality, 2),
            "composite": round(breakdown.composite, 2),
        },
        "raw": {k: float(v) for k, v in raw.items()},
        "vs_reference": {
            "speed_ratio": round(ratio, 3),
            "slower_than_normal_pct": round(slower_pct, 1),
            "smoother_ratio": round(smoother_ratio, 3),
        },
    }


def analyze_one_landmarks(landmarks, fps: float,
                          baseline: Optional[ReferenceBaseline] = None) -> dict:
    bl = baseline or get_reference_baseline()
    traj = trajectories_from_landmarks(landmarks, fps, "patient")
    return _one_report(traj, bl)


def analyze_one_video(path: str,
                      baseline: Optional[ReferenceBaseline] = None) -> dict:
    from ai.tracking.hand_tracker import extract_hand_samples, samples_to_overlay, samples_to_trajectories
    bl = baseline or get_reference_baseline()
    fps, detections = extract_hand_samples(path)
    hands = samples_to_trajectories(fps, detections)
    if not hands:
        raise ValueError(f"no hand detected in video: {path}")
    report = _one_report(hands[0].trajectory, bl)
    # overlay = per-frame image landmarks from the SAME pass (no second run)
    report["overlay"] = {"fps": round(fps, 3), "frames": samples_to_overlay(detections)}
    return report
