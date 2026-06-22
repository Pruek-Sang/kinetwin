"""Unit tests for the tracking-conversion + analysis pipeline.

These do **not** need MediaPipe or a real video: they feed synthetic landmark
detections through the pure-Python parts (:func:`samples_to_trajectories` and
:func:`analyze_trajectories`) to prove the wiring and the report schema.
"""
from __future__ import annotations

import numpy as np
import pytest

from ai.metrics import HandTrajectory, ReferenceBaseline
from ai.pipeline import analyze_trajectories
from ai.tracking import FrameDetection, samples_to_trajectories

from ai.tests.conftest import impaired_trajectory, normal_trajectory


# --------------------------------------------------------------- conversion
def _detections_from_trajectory(traj: HandTrajectory, label: str, start: int = 0):
    """Build FrameDetection stream that reproduces ``traj`` for one hand."""
    dummy_image = [[0.0, 0.0]] * 21  # image landmarks not used by the trajectory path
    return [
        FrameDetection(frame_index=start + t, hands=((label, traj.landmarks[t], dummy_image),))
        for t in range(traj.n_frames)
    ]


def test_samples_to_trajectories_groups_two_hands():
    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    fps = normal.fps
    # Interleave two hands across the same frames.
    length = min(normal.n_frames, impaired.n_frames)
    detections = [
        FrameDetection(
            frame_index=t,
            hands=(
                ("Right", normal.landmarks[t], [[0.0, 0.0]] * 21),
                ("Left", impaired.landmarks[t], [[0.0, 0.0]] * 21),
            ),
        )
        for t in range(length)
    ]
    tracked = samples_to_trajectories(fps, detections)
    labels = sorted(t.handedness for t in tracked)
    assert labels == ["Left", "Right"]
    by_label = {t.handedness: t for t in tracked}
    assert by_label["Right"].trajectory.n_frames == length
    assert by_label["Left"].trajectory.n_frames == length


def test_samples_to_trajectories_drops_short_hands():
    det = [FrameDetection(frame_index=0, hands=(("Right", np.zeros((21, 3)), np.zeros((21, 2))),))]
    assert samples_to_trajectories(30.0, det, min_frames=2) == []


def test_samples_to_trajectories_skips_frames_with_no_hand():
    normal = normal_trajectory()
    dets = _detections_from_trajectory(normal, "Right")
    # Poke a hole in the middle (no hand detected on one frame).
    dets[len(dets) // 2] = FrameDetection(frame_index=len(dets) // 2, hands=())
    tracked = samples_to_trajectories(normal.fps, dets)
    assert len(tracked) == 1
    # The hole is dropped -> one fewer frame than the source.
    assert tracked[0].trajectory.n_frames == normal.n_frames - 1


# ------------------------------------------------------------------ pipeline
def test_analyze_trajectories_report_shape():
    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    baseline = ReferenceBaseline.from_trajectory(normal)
    report = analyze_trajectories(left=impaired, right=normal, baseline=baseline)

    assert set(report.keys()) >= {
        "metrics", "dominant_hand", "score_gap", "learned_non_use",
    }
    assert set(report["metrics"].keys()) == {"left", "right"}
    for side in ("left", "right"):
        side_metrics = report["metrics"][side]
        assert set(side_metrics.keys()) == {
            "speed", "accuracy", "quality", "composite", "raw",
        }
        assert set(side_metrics["raw"].keys()) == {
            "mean_speed", "straightness", "dimensionless_jerk",
            "smoothness_index", "velocity_peaks",
        }


def test_analyze_trajectories_flags_learned_non_use():
    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    baseline = ReferenceBaseline.from_trajectory(normal)
    report = analyze_trajectories(left=impaired, right=normal, baseline=baseline)

    assert report["dominant_hand"] == "right"
    assert report["learned_non_use"]["flag"] is True
    assert report["learned_non_use"]["hand"] == "left"
    assert report["score_gap"] > 0


def test_analyze_trajectories_works_without_explicit_baseline():
    # When no baseline is given, the stronger hand becomes the reference.
    a = normal_trajectory(label="right", seed=3)
    b = normal_trajectory(label="left", seed=4)
    report = analyze_trajectories(left=b, right=a)
    assert report["dominant_hand"] in {"left", "right"}
    assert report["learned_non_use"]["flag"] is False


def test_analyze_trajectories_accepts_tracked_hand_objects():
    normal = normal_trajectory(label="right")
    impaired = impaired_trajectory(label="left")
    baseline = ReferenceBaseline.from_trajectory(normal)
    dets_r = _detections_from_trajectory(normal, "Right")
    dets_l = _detections_from_trajectory(impaired, "Left")
    right_hand = samples_to_trajectories(normal.fps, dets_r)[0]
    left_hand = samples_to_trajectories(impaired.fps, dets_l)[0]

    report = analyze_trajectories(left=left_hand, right=right_hand, baseline=baseline)
    assert report["dominant_hand"] == "right"
    assert report["learned_non_use"]["flag"] is True
