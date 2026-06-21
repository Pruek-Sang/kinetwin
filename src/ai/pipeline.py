"""End-to-end analysis pipeline: tracking -> metrics -> Learned Non-Use report.

Two entry points:

* :func:`analyze_trajectories` -- pure, video-free. Takes already-tracked
  :class:`~ai.metrics.HandTrajectory` objects (or
  :class:`~ai.tracking.TrackedHand`), scores them against a baseline and
  returns a JSON-serialisable report. This is the function the FastAPI layer
  and the unit tests use.
* :func:`analyze_videos` -- convenience wrapper that runs MediaPipe tracking on
  two video files first, then calls :func:`analyze_trajectories`.

The report schema is intentionally flat so the FastAPI response model and the
React frontend can consume it directly.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable, Optional, Union

from .metrics import (
    DEFAULT_LEARNED_NON_USE_GAP,
    DEFAULT_WEIGHTS,
    HandTrajectory,
    HandComparison,
    MetricBreakdown,
    ReferenceBaseline,
    compare_hands,
    raw_metrics,
)
from .tracking import TrackedHand, track_video

HandLike = Union[HandTrajectory, TrackedHand]


def _trajectory(hand: HandLike) -> HandTrajectory:
    if isinstance(hand, TrackedHand):
        return hand.trajectory
    return hand


def _breakdown_dict(b: MetricBreakdown) -> dict:
    return {
        "speed": round(b.speed, 2),
        "accuracy": round(b.accuracy, 2),
        "quality": round(b.quality, 2),
        "composite": round(b.composite, 2),
        "raw": {k: float(v) for k, v in b.raw.items()},
    }


def analyze_trajectories(
    left: HandLike,
    right: HandLike,
    baseline: Optional[ReferenceBaseline] = None,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    learned_non_use_gap: float = DEFAULT_LEARNED_NON_USE_GAP,
) -> dict:
    """Score the left/right hands and return a flat JSON-serialisable report.

    If ``baseline`` is ``None`` the *better* of the two hands is used as the
    reference (useful when no external ideal/reference exists). For an absolute
    score, pass a :class:`ReferenceBaseline` built from the Blender reference.
    """
    left_traj = _trajectory(left)
    right_traj = _trajectory(right)

    if baseline is None:
        # Use the stronger hand as the ad-hoc reference.
        from .metrics import wrist_mean_speed, path_straightness, dimensionless_jerk  # local

        def _baseline_of(t: HandTrajectory) -> ReferenceBaseline:
            return ReferenceBaseline(
                mean_speed=wrist_mean_speed(t),
                dimensionless_jerk=dimensionless_jerk(t),
            )

        bl = _baseline_of(left_traj)
        br = _baseline_of(right_traj)
        # "Stronger" = higher composite when scored against the other. Cheap
        # heuristic: pick the hand with the larger mean_speed*straightness.
        score_l = wrist_mean_speed(left_traj) * path_straightness(left_traj)
        score_r = wrist_mean_speed(right_traj) * path_straightness(right_traj)
        baseline = bl if score_l >= score_r else br

    comparison: HandComparison = compare_hands(
        left_traj, right_traj, baseline, weights, learned_non_use_gap
    )

    return {
        "metrics": {
            "left": _breakdown_dict(comparison.left),
            "right": _breakdown_dict(comparison.right),
        },
        "dominant_hand": comparison.dominant_label,
        "score_gap": round(comparison.gap, 2),
        "learned_non_use": {
            "flag": comparison.learned_non_use_flag,
            "hand": comparison.learned_non_use_label,
        },
        "weights": dict(weights),
        "learned_non_use_gap_threshold": learned_non_use_gap,
    }


def analyze_videos(
    left_video: str,
    right_video: str,
    baseline: Optional[ReferenceBaseline] = None,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    learned_non_use_gap: float = DEFAULT_LEARNED_NON_USE_GAP,
) -> dict:
    """Track two videos and analyse them. Needs ``mediapipe``/``opencv``.

    Each video is expected to show exactly one hand (the dedicated-task
    recording). If a video yields multiple tracked hands the *first* is used.
    """
    def _first(path: str) -> HandTrajectory:
        hands = track_video(path)
        if not hands:
            raise ValueError(f"no hand detected in video: {path}")
        return hands[0].trajectory

    return analyze_trajectories(
        _first(left_video), _first(right_video), baseline, weights, learned_non_use_gap
    )


__all__ = ["analyze_trajectories", "analyze_videos"]
