"""Trajectory data model + small geometry helpers used by every metric.

A :class:`HandTrajectory` is just a ``(T, 21, 3)`` array of landmark positions
sampled at a constant frame rate, plus that frame rate. All metric functions
take a :class:`HandTrajectory` so the contract is uniform between the video
tracker and the Blender reference exporter.

Units contract
--------------
Landmarks are assumed to be in a *consistent real-world unit* (metres) and in a
*consistent world frame* across the two hands being compared. Ratios (speed,
straightness, smoothness) are dimensionless or unit/time and compare fairly as
long as both hands share the same calibration. If only normalised image
coordinates are available, callers must rescale to a common world scale before
constructing the trajectory.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .landmarks import WRIST

_EPS: float = 1e-9

#: Default moving-average window (frames) used to de-noise landmark positions
#: before any derivative / length computation. Real MediaPipe landmarks jitter;
#: a small window removes sensor noise without erasing real low-frequency
#: movement. Set to <= 1 to disable smoothing.
DEFAULT_SMOOTH_WINDOW: int = 11


@dataclass(frozen=True)
class HandTrajectory:
    """Sampled hand-landmark trajectory.

    Attributes
    ----------
    landmarks:
        Array of shape ``(T, 21, 3)``. ``T >= 2`` for any derivative-based
        metric. ``landmarks[t, i]`` is the 3D position of landmark ``i`` at
        frame ``t``.
    fps:
        Constant sampling rate in Hz. ``dt = 1 / fps``.
    label:
        Optional human label, e.g. ``"left"``/``"right"``/``"reference"``.
    """

    landmarks: np.ndarray
    fps: float
    label: str = ""

    def __post_init__(self) -> None:
        arr = np.asarray(self.landmarks, dtype=float)
        if arr.ndim != 3 or arr.shape[1] != 21 or arr.shape[2] != 3:
            raise ValueError(
                f"landmarks must have shape (T, 21, 3); got {arr.shape}"
            )
        if arr.shape[0] < 2:
            raise ValueError("need at least 2 frames to compute derivatives")
        if self.fps <= 0:
            raise ValueError(f"fps must be positive; got {self.fps}")
        # Re-bind the validated array (frozen dataclass workaround).
        object.__setattr__(self, "landmarks", arr)
        object.__setattr__(self, "fps", float(self.fps))

    # ------------------------------------------------------------------ basic
    @property
    def n_frames(self) -> int:
        return int(self.landmarks.shape[0])

    @property
    def dt(self) -> float:
        return 1.0 / self.fps

    @property
    def duration(self) -> float:
        """Total span of the recording, in seconds ``(T-1)/fps``."""
        return (self.n_frames - 1) / self.fps

    @property
    def times(self) -> np.ndarray:
        """Per-frame timestamps, shape ``(T,)``."""
        return np.arange(self.n_frames, dtype=float) / self.fps

    # --------------------------------------------------------------- accessors
    def wrist(self) -> np.ndarray:
        """Wrist positions over time, shape ``(T, 3)``."""
        return self.landmarks[:, WRIST, :]

    def landmark(self, index: int) -> np.ndarray:
        """Positions of a single landmark over time, shape ``(T, 3)``."""
        return self.landmarks[:, index, :]


# --------------------------------------------------------------------- helpers
def path_length(points: np.ndarray) -> float:
    """Cumulative Euclidean length of a polyline, shape ``(T, D)``."""
    pts = np.asarray(points, dtype=float)
    if pts.shape[0] < 2:
        return 0.0
    return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))


def net_displacement(points: np.ndarray) -> float:
    """Straight-line distance between first and last point."""
    pts = np.asarray(points, dtype=float)
    return float(np.linalg.norm(pts[-1] - pts[0]))


def speed_profile(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> np.ndarray:
    """Scalar speed (unit/s) of one landmark per inter-frame interval.

    The landmark path is lightly smoothed (moving average) first so that sensor
    jitter does not inflate the per-frame speed. Returns length ``T-1``.
    """
    pts = smooth_points(traj.landmark(landmark_index), smooth_window)
    steps = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    return steps / traj.dt


def derivative(points: np.ndarray, dt: float, order: int = 1) -> np.ndarray:
    """Central-difference derivative of a ``(T, D)`` signal, ``order`` times."""
    arr = np.asarray(points, dtype=float)
    for _ in range(order):
        arr = np.gradient(arr, dt, axis=0)
    return arr


def smooth_points(points: np.ndarray, window: int = DEFAULT_SMOOTH_WINDOW) -> np.ndarray:
    """Moving-average smoothing of a ``(T, D)`` signal along time.

    ``window <= 1`` or shorter than the signal returns the input unchanged.
    Edges are *edge-padded* (replicate the endpoint value) rather than
    zero-padded, so smoothing does not create transients that would depress
    path-straightness or inflate jerk at the start/end of the recording.
    """
    pts = np.asarray(points, dtype=float)
    if window <= 1 or pts.shape[0] < window:
        return pts
    pad = window // 2
    kernel = np.ones(window, dtype=float) / float(window)
    out = np.empty_like(pts)
    for axis in range(pts.shape[1]):
        col = np.pad(pts[:, axis], pad, mode="edge")
        out[:, axis] = np.convolve(col, kernel, mode="valid")
    return out
