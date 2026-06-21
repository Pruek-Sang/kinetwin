"""Load the Blender reference-hand trajectory exported as JSON.

The Blender script ``src/deploy/blender/animate_reference_hand.py`` writes a
21-landmark trajectory (MediaPipe schema, metres) to
``reference_hand_trajectory.json``. This loader turns it into a
:class:`~ai.metrics.HandTrajectory` so the metrics pipeline can score the
"ideal / normal" reference exactly like a patient video.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

from ..metrics import HandTrajectory

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "reference_hand_trajectory.json")


def load_reference_trajectory(path: Optional[str] = None) -> HandTrajectory:
    """Load the exported reference trajectory into a :class:`HandTrajectory`."""
    p = path or DEFAULT_PATH
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    landmarks = np.asarray([frame["landmarks"] for frame in data["frames"]], dtype=float)
    return HandTrajectory(
        landmarks=landmarks,
        fps=float(data.get("fps", 30.0)),
        label=data.get("label", "reference"),
    )


__all__ = ["load_reference_trajectory", "DEFAULT_PATH"]
