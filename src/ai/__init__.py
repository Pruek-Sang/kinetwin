"""KineTwin AI layer.

Two sub-packages:

* :mod:`ai.metrics`   -- pure-Python movement metrics (Speed/Accuracy/Quality).
* :mod:`ai.tracking`  -- MediaPipe Hands video -> landmark wrapper (added in a
  later slice). The metrics package has *no* MediaPipe/OpenCV dependency so it
  can be unit-tested with synthetic landmarks.
"""
from __future__ import annotations
