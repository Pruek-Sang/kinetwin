"""KineTwin hand-movement metrics.

Pure-Python, dependency-light functions that turn a
:class:`~ai.metrics.trajectory.HandTrajectory` (a ``(T, 21, 3)`` landmark array
sampled at a known frame rate) into the three metrics the hackathon brief asks
for -- **Speed**, **Accuracy**, **Quality of movement** -- plus grasp-aperture
helpers and a composite dexterity score for Learned Non-Use detection.

Import the high-level helpers directly::

    from ai.metrics import (
        HandTrajectory,
        score_hand,
        compare_hands,
        ReferenceBaseline,
        raw_metrics,
    )
"""
from __future__ import annotations

from .accuracy import path_straightness, target_error
from .grasp import aperture_peak_time, aperture_range, grasp_aperture_series
from .landmarks import (
    FINGER_MCPS,
    FINGER_TIPS,
    GRASP_APERTURE_PAIR,
    LANDMARK_NAMES,
    N_LANDMARKS,
    WRIST,
)
from .quality import (
    MIN_JERK_NC,
    dimensionless_jerk,
    jerk_magnitude_profile,
    mean_squared_jerk,
    smoothness_index,
    velocity_peaks,
)
from .score import (
    DEFAULT_LEARNED_NON_USE_GAP,
    DEFAULT_WEIGHTS,
    HandComparison,
    MetricBreakdown,
    ReferenceBaseline,
    compare_hands,
    raw_metrics,
    score_hand,
)
from .speed import task_duration_seconds, wrist_mean_speed, wrist_peak_speed
from .trajectory import (
    HandTrajectory,
    derivative,
    net_displacement,
    path_length,
    speed_profile,
)

__all__ = [
    # trajectory + constants
    "HandTrajectory",
    "WRIST",
    "N_LANDMARKS",
    "LANDMARK_NAMES",
    "FINGER_TIPS",
    "FINGER_MCPS",
    "GRASP_APERTURE_PAIR",
    # speed
    "task_duration_seconds",
    "wrist_mean_speed",
    "wrist_peak_speed",
    # accuracy
    "path_straightness",
    "target_error",
    # quality
    "smoothness_index",
    "dimensionless_jerk",
    "mean_squared_jerk",
    "MIN_JERK_NC",
    "velocity_peaks",
    "jerk_magnitude_profile",
    # grasp
    "grasp_aperture_series",
    "aperture_range",
    "aperture_peak_time",
    # score
    "raw_metrics",
    "score_hand",
    "compare_hands",
    "ReferenceBaseline",
    "MetricBreakdown",
    "HandComparison",
    "DEFAULT_WEIGHTS",
    "DEFAULT_LEARNED_NON_USE_GAP",
    # helpers
    "speed_profile",
    "derivative",
    "path_length",
    "net_displacement",
]
