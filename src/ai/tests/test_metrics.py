"""Unit tests for the KineTwin movement metrics.

These prove the three contract properties the rest of the system relies on:

1. **Metrics are sane** -- they live in their documented ranges and behave on
   trivial inputs (a perfectly straight, constant-velocity path is straight and
   smooth).
2. **Metrics discriminate** -- a healthy synthetic reach beats an impaired one
   on Speed, Accuracy *and* Quality.
3. **The scorer flags Learned Non-Use** -- :func:`compare_hands` identifies the
   weaker hand and raises the flag when the gap is large enough.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from ai.metrics import (
    DEFAULT_LEARNED_NON_USE_GAP,
    DEFAULT_WEIGHTS,
    HandTrajectory,
    MIN_JERK_NC,
    ReferenceBaseline,
    aperture_range,
    compare_hands,
    dimensionless_jerk,
    grasp_aperture_series,
    path_straightness,
    raw_metrics,
    score_hand,
    smoothness_index,
    velocity_peaks,
    wrist_mean_speed,
)

from .conftest import impaired_trajectory, normal_trajectory


# ----------------------------------------------------------------------- sanity
def test_hand_trajectory_validates_shape():
    bad = np.zeros((10, 20, 3))
    with pytest.raises(ValueError):
        HandTrajectory(landmarks=bad, fps=30.0)


def test_hand_trajectory_validates_fps():
    good = np.zeros((10, 21, 3))
    with pytest.raises(ValueError):
        HandTrajectory(landmarks=good, fps=0.0)


def test_straightness_is_bounded_unit_interval():
    traj = normal_trajectory()
    sp = path_straightness(traj)
    assert 0.0 < sp <= 1.0


def test_smooth_straight_reach_is_straight_and_smooth():
    # A minimum-jerk reach (the profile healthy humans use) along a line:
    # perfectly straight, and its dimensionless jerk sits near the theoretical
    # floor MIN_JERK_NC (720). Light smoothing can pull it a little *below* 720
    # (the signal becomes numerically smoother than the raw minimum-jerk), so we
    # assert it stays within 1.5x of the floor and is finite/positive.
    n, fps = 60, 30.0
    lm = np.zeros((n, 21, 3))
    s = np.linspace(0.0, 1.0, n)
    mj = s * s * s * (10.0 - s * (15.0 - s * 6.0))  # 10s^3 - 15s^4 + 6s^5
    lm[:, 0, 0] = 0.30 * mj
    traj = HandTrajectory(landmarks=lm, fps=fps)
    assert path_straightness(traj) == pytest.approx(1.0, abs=1e-4)
    nc = dimensionless_jerk(traj)
    assert math.isfinite(nc) and nc > 0.0
    assert nc < 1.5 * MIN_JERK_NC
    # ... and it is much smoother than the impaired fixture.
    assert nc < dimensionless_jerk(impaired_trajectory())


# ----------------------------------------------------------------- discriminant
def test_normal_is_faster_than_impaired():
    normal = normal_trajectory()
    impaired = impaired_trajectory()
    assert wrist_mean_speed(normal) > wrist_mean_speed(impaired)


def test_normal_is_straighter_than_impaired():
    normal = normal_trajectory()
    impaired = impaired_trajectory()
    assert path_straightness(normal) > path_straightness(impaired)


def test_normal_is_smoother_than_impaired():
    normal = normal_trajectory()
    impaired = impaired_trajectory()
    assert smoothness_index(normal) > smoothness_index(impaired)


def test_normal_has_fewer_velocity_peaks_than_impaired():
    normal = normal_trajectory()
    impaired = impaired_trajectory()
    assert velocity_peaks(normal) <= velocity_peaks(impaired)


def test_normal_has_larger_grasp_aperture_range():
    # A healthy hand opens wider during transport than a clenched impaired hand.
    normal = normal_trajectory()
    impaired = impaired_trajectory()
    assert aperture_range(normal) > aperture_range(impaired)


def test_grasp_aperture_series_shape_and_sign():
    traj = normal_trajectory()
    series = grasp_aperture_series(traj)
    assert series.shape == (traj.n_frames,)
    assert np.all(series > 0)


# ------------------------------------------------------------------------ score
def test_score_hand_normal_scores_high_against_self_baseline():
    normal = normal_trajectory()
    baseline = ReferenceBaseline.from_trajectory(normal)
    breakdown = score_hand(normal, baseline)
    # A trajectory scored against its own baseline must be ~perfect (>=90).
    assert breakdown.composite >= 90.0
    assert 0.0 <= breakdown.speed <= 100.0
    assert 0.0 <= breakdown.accuracy <= 100.0
    assert 0.0 <= breakdown.quality <= 100.0


def test_score_hand_impaired_scores_lower_than_normal():
    normal = normal_trajectory()
    impaired = impaired_trajectory()
    baseline = ReferenceBaseline.from_trajectory(normal)
    assert score_hand(normal, baseline).composite > score_hand(impaired, baseline).composite


def test_raw_metrics_returns_expected_keys():
    traj = normal_trajectory()
    raw = raw_metrics(traj)
    assert set(raw.keys()) == {
        "mean_speed",
        "straightness",
        "dimensionless_jerk",
        "smoothness_index",
        "velocity_peaks",
    }


def test_compare_hands_flags_learned_non_use_on_weaker_side():
    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    baseline = ReferenceBaseline.from_trajectory(normal)

    comparison = compare_hands(left=impaired, right=normal, baseline=baseline)

    # The healthy hand is dominant.
    assert comparison.dominant_label == "right"
    # The impaired hand should be flagged as a Learned Non-Use candidate.
    assert comparison.learned_non_use_flag is True
    assert comparison.learned_non_use_label == "left"
    # And the gap should clear the default threshold.
    assert comparison.gap >= DEFAULT_LEARNED_NON_USE_GAP


def test_compare_hands_does_not_flag_two_similar_hands():
    a = normal_trajectory(label="left", seed=10)
    b = normal_trajectory(label="right", seed=11)
    baseline = ReferenceBaseline.from_trajectory(a)
    comparison = compare_hands(left=a, right=b, baseline=baseline)
    assert comparison.learned_non_use_flag is False
    assert comparison.gap < DEFAULT_LEARNED_NON_USE_GAP


def test_default_weights_sum_to_one():
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)
