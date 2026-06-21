"""Accuracy metrics.

Without external ground-truth target coordinates (which we do not require the
patient to mark), the cleanest *video-only* proxy for accuracy of a
reach-to-grasp movement is **path straightness**: how close the hand path is to
the ideal straight line from start to target.

* :func:`path_straightness` -- ``net_displacement / path_length`` in ``(0, 1]``.
  ``1.0`` is a perfectly straight reach; a meandering / corrective hand (typical
  of an impaired side) drops well below 1.
* :func:`target_error` -- optional, when a known target position is supplied
  (e.g. the cup centre from the Blender reference), returns the final wrist
  distance to that target.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .landmarks import WRIST
from .trajectory import DEFAULT_SMOOTH_WINDOW, HandTrajectory, net_displacement, path_length, smooth_points

_EPS: float = 1e-9


def path_straightness(
    traj: HandTrajectory,
    landmark_index: int = WRIST,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> float:
    """Ratio of net displacement to travelled path length, in ``(0, 1]``.

    The wrist path is lightly smoothed first so jitter does not depress the
    ratio. Higher is straighter (more accurate reach).
    """
    pts = smooth_points(traj.landmark(landmark_index), smooth_window)
    length = path_length(pts)
    if length <= _EPS:
        return 1.0
    return float(np.clip(net_displacement(pts) / length, 0.0, 1.0))


def target_error(
    traj: HandTrajectory,
    target: np.ndarray,
    landmark_index: int = WRIST,
    when: str = "final",
) -> float:
    """Distance from the wrist to a known ``target`` (shape ``(3,)``).

    ``when``:
      * ``"final"`` (default) -- distance at the last frame,
      * ``"min"``   -- closest approach at any frame.
    """
    target = np.asarray(target, dtype=float).reshape(3)
    pts = traj.landmark(landmark_index)
    dists = np.linalg.norm(pts - target, axis=1)
    if when == "min":
        return float(dists.min())
    return float(dists[-1])
