"""Quality-of-movement (smoothness) metrics.

Movement quality is operationalised as **smoothness**, the standard construct in
upper-limb motor-control research. The fundamental quantity is the
**dimensionless jerk** (a.k.a. normalised jerk)::

    NC = MSJ * T^6 / D^2

where ``MSJ`` is the mean-squared jerk magnitude, ``T`` the duration and ``D``
the net displacement. ``NC`` is positive, **scale- and rate-invariant** and
**lower = smoother**. The theoretical minimum is ``NC = 720`` attained by a
minimum-jerk trajectory (the profile healthy humans produce); impaired reaches
fragment into corrective sub-movements and produce a much larger ``NC``.

Two user-facing views are derived from ``NC``:

* :func:`dimensionless_jerk` -- the raw ``NC`` (lower = smoother; used for
  scoring, since it is always positive and monotonic).
* :func:`smoothness_index` -- ``LDJ = -ln(NC)`` (higher = smoother; for
  display). A minimum-jerk reach scores ``-ln(720) ~= -6.58``.
* :func:`velocity_peaks` -- count of distinct sub-movement peaks in the wrist
  speed profile (fewer = smoother). A clean reach has ~1 peak.

All are computed from the wrist landmark via central-difference derivatives on a
lightly smoothed path.
"""
from __future__ import annotations

import math

import numpy as np

from .landmarks import WRIST
from .trajectory import (
    DEFAULT_SMOOTH_WINDOW,
    HandTrajectory,
    derivative,
    net_displacement,
    smooth_points,
    speed_profile,
)

_EPS: float = 1e-9

#: The dimensionless-jerk value of a perfect minimum-jerk trajectory
#: (``integral jerk^2 = 720 D^2 / T^5``). Real healthy reaches sit just above it.
MIN_JERK_NC: float = 720.0


def mean_squared_jerk(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> float:
    """Mean squared jerk magnitude of the wrist path (units ``(unit/s^3)^2``)."""
    pts = smooth_points(traj.landmark(landmark_index), smooth_window)
    jerk = derivative(pts, traj.dt, order=3)  # (T, 3)
    return float(np.mean(np.sum(jerk * jerk, axis=1)))


def jerk_magnitude_profile(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> np.ndarray:
    """Magnitude of the 3rd time-derivative of position per frame, shape ``(T,)``."""
    pts = smooth_points(traj.landmark(landmark_index), smooth_window)
    jerk = derivative(pts, traj.dt, order=3)
    return np.linalg.norm(jerk, axis=1)


def dimensionless_jerk(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> float:
    """Dimensionless (normalised) jerk ``NC = MSJ * T^6 / D^2``.

    Positive, scale- and rate-invariant. **Lower = smoother.** The theoretical
    floor is :data:`MIN_JERK_NC` (720) for a minimum-jerk reach. Returns
    ``+inf`` for degenerate (stationary / zero-net-displacement) motion.
    """
    pts = smooth_points(traj.landmark(landmark_index), smooth_window)
    duration = traj.duration
    net = net_displacement(pts)
    if duration <= _EPS or net <= _EPS:
        return float("inf")

    jerk = derivative(pts, traj.dt, order=3)  # (T, 3)
    msj = float(np.mean(np.sum(jerk * jerk, axis=1)))
    if msj <= _EPS:
        return MIN_JERK_NC  # numerically perfect motion -> theoretical floor
    return msj * (duration ** 6) / (net * net)


def smoothness_index(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> float:
    """Log dimensionless jerk ``LDJ = -ln(NC)``. **Higher = smoother.**

    A minimum-jerk reach scores ``-ln(720) ~= -6.58``; impaired reaches score
    lower (more negative). Returns ``-inf`` for degenerate motion.
    """
    nc = dimensionless_jerk(traj, landmark_index, smooth_window)
    if not math.isfinite(nc) or nc <= 0:
        return float("-inf")
    return float(-math.log(nc))


def velocity_peaks(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    rel_prominence: float = 0.15,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> int:
    """Number of local maxima in the wrist speed profile.

    A sub-movement peak only counts if it rises above
    ``rel_prominence * peak_speed`` to avoid counting jitter. Fewer = smoother.
    """
    sp = speed_profile(traj, landmark_index, smooth_window=smooth_window)
    if sp.size < 3:
        return 0
    peak_speed = float(sp.max())
    if peak_speed <= _EPS:
        return 0
    threshold = peak_speed * rel_prominence

    count = 0
    for i in range(1, sp.size - 1):
        if sp[i] > sp[i - 1] and sp[i] >= sp[i + 1] and sp[i] >= threshold:
            count += 1
    return count
