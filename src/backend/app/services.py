"""Service layer: wraps the ai pipeline and the reference baseline.

The "normal" reference is the Blender-exported trajectory
(``reference_hand_trajectory.json``); patient videos are scored against it so the
numbers are absolute, not just relative to the patient's own two hands.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import numpy as np

from ai.metrics import DEFAULT_LEARNED_NON_USE_GAP, DEFAULT_WEIGHTS, HandTrajectory, ReferenceBaseline
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
