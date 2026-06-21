"""Grasp-aperture helpers.

During *Reach -> Grasp -> Lift* the hand first opens (transport aperture) then
closes around the cup. The thumb-tip <-> index-tip distance (the MediaPipe
"grasp aperture pair") captures this opening/closing. A healthy grasp shows a
clear, well-timed aperture peak-then-close; an impaired hand either fails to
open (small range) or closes late / incompletely.
"""
from __future__ import annotations

import numpy as np

from .landmarks import GRASP_APERTURE_PAIR
from .trajectory import HandTrajectory


def grasp_aperture_series(traj: HandTrajectory) -> np.ndarray:
    """Per-frame thumb-tip <-> index-tip distance, shape ``(T,)``."""
    a, b = GRASP_APERTURE_PAIR
    pa = traj.landmark(a)
    pb = traj.landmark(b)
    return np.linalg.norm(pa - pb, axis=1)


def aperture_range(traj: HandTrajectory) -> float:
    """Difference between maximum and minimum aperture over the task.

    Larger = the hand actually opened and closed (healthy). Near-zero = the
    hand stayed clenched or stayed open (impaired).
    """
    ap = grasp_aperture_series(traj)
    return float(ap.max() - ap.min())


def aperture_peak_time(traj: HandTrajectory) -> float:
    """Timestamp (seconds) at which the hand is widest (reach transport peak)."""
    ap = grasp_aperture_series(traj)
    return float(np.argmax(ap)) / traj.fps
