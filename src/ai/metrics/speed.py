"""Speed metrics.

For the *Reach -> Grasp -> Lift* task the clinically meaningful speed measures
are:

* **task duration** -- total time to complete one cycle (lower = faster),
* **mean wrist speed** -- average translational speed of the hand,
* **peak wrist speed** -- fastest instantaneous speed during the reach.

All three are computed from the wrist landmark (index 0). A "slower" hand
(Learned Non-Use candidate) shows lower mean/peak speed and longer duration.
"""
from __future__ import annotations

from .landmarks import WRIST
from .trajectory import DEFAULT_SMOOTH_WINDOW, HandTrajectory, path_length, smooth_points, speed_profile


def task_duration_seconds(traj: HandTrajectory) -> float:
    """Total recording duration in seconds."""
    return traj.duration


def wrist_mean_speed(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> float:
    """Mean translational speed of the wrist over the whole task (unit/s).

    Computed as ``smoothed_path_length / duration`` so that MediaPipe jitter
    does not inflate the speed (raw per-frame averaging would).
    """
    if traj.duration <= 0:
        return 0.0
    pts = smooth_points(traj.landmark(landmark_index), smooth_window)
    return path_length(pts) / traj.duration


def wrist_peak_speed(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> float:
    """Peak instantaneous wrist speed (unit/s), after light smoothing."""
    sp = speed_profile(traj, landmark_index, smooth_window=smooth_window)
    if sp.size == 0:
        return 0.0
    return float(sp.max())
