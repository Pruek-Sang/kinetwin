"""Synthetic landmark-trajectory factories for metric unit tests.

These produce realistic *Reach -> Grasp -> Lift* hand trajectories without any
video or MediaPipe, so the metric math can be tested in isolation:

* :func:`normal_trajectory` -- a fast, straight, single-bell reach with a clean
  grasp open/close. High speed, high straightness, high smoothness.
* :func:`impaired_trajectory` -- the same task but slower, with added jitter and
  a curved, corrective path. Low speed, low straightness, low smoothness.

Only the wrist + thumb-tip + index-tip landmarks are meaningfully animated; the
remaining 18 landmarks are placed relative to the wrist so the array stays a
valid ``(T, 21, 3)`` shape (they are not used by the metrics under test).
"""
from __future__ import annotations

import numpy as np

from ai.metrics import HandTrajectory
from ai.metrics.landmarks import INDEX_TIP, THUMB_TIP, WRIST

DEFAULT_FPS: float = 30.0


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """Monotonic 0..1 S-curve, C1-smooth (zero velocity at both ends)."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _minimum_jerk(t: np.ndarray) -> np.ndarray:
    """Minimum-jerk point-to-point profile, ``10t^3 - 15t^4 + 6t^5``.

    This is the trajectory healthy humans actually produce for a reach (it
    minimises the integral of squared jerk), so it yields a *high, positive*
    smoothness index. We use it for the "normal" hand so the quality score is
    meaningful, in contrast to the impaired hand which uses the rougher
    smoothstep plus wobble and jitter.
    """
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (10.0 - t * (15.0 - t * 6.0))


def _build_landmarks(
    n_frames: int,
    wrist_xy: np.ndarray,
    aperture: np.ndarray,
    jitter_std: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Assemble a ``(T, 21, 3)`` array from wrist + aperture schedules.

    ``wrist_xy`` is ``(T, 2)`` wrist positions in the XY plane (Z=0).
    ``aperture`` is ``(T,)`` the thumb/index spread at each frame.
    """
    lm = np.zeros((n_frames, 21, 3), dtype=float)
    lm[:, WRIST, 0] = wrist_xy[:, 0]
    lm[:, WRIST, 1] = wrist_xy[:, 1]

    # Anchor every other landmark at a fixed offset from the wrist so the array
    # is well-formed. Only thumb-tip and index-tip are driven by the aperture.
    for i in range(21):
        if i in (WRIST, THUMB_TIP, INDEX_TIP):
            continue
        lm[:, i, :] = lm[:, WRIST, :] + np.array([0.02, -0.01, 0.0])

    half = aperture / 2.0
    lm[:, THUMB_TIP, 0] = lm[:, WRIST, 0] - half
    lm[:, THUMB_TIP, 1] = lm[:, WRIST, 1] + 0.04
    lm[:, INDEX_TIP, 0] = lm[:, WRIST, 0] + half
    lm[:, INDEX_TIP, 1] = lm[:, WRIST, 1] + 0.04

    if jitter_std > 0:
        lm += rng.normal(0.0, jitter_std, size=lm.shape)
    return lm


def normal_trajectory(
    fps: float = DEFAULT_FPS,
    duration: float = 1.5,
    distance: float = 0.30,
    seed: int = 0,
    label: str = "normal",
) -> HandTrajectory:
    """A healthy reach-grasp-lift: straight, fast, single smooth bell."""
    n_frames = max(2, int(round(duration * fps)))
    t = np.linspace(0.0, 1.0, n_frames)

    # Straight-line reach forward (minimum-jerk profile) then a small lift.
    s = _minimum_jerk(t)
    lift = 0.03 * np.sin(np.pi * s)  # gentle arc up and back
    x = distance * s
    y = lift
    wrist_xy = np.stack([x, y], axis=1)

    # Aperture: opens wide during reach (transport), closes to grasp at the end.
    aperture = 0.085 * (1.0 - s) + 0.01

    rng = np.random.default_rng(seed)
    lm = _build_landmarks(n_frames, wrist_xy, aperture, jitter_std=0.0, rng=rng)
    return HandTrajectory(landmarks=lm, fps=fps, label=label)


def impaired_trajectory(
    fps: float = DEFAULT_FPS,
    duration: float = 3.0,
    distance: float = 0.30,
    jitter_std: float = 0.004,
    curvature: float = 0.06,
    seed: int = 1,
    label: str = "impaired",
) -> HandTrajectory:
    """A Learned Non-Use side: slow, jittery, corrective (curved) path."""
    n_frames = max(2, int(round(duration * fps)))
    t = np.linspace(0.0, 1.0, n_frames)

    s = _smoothstep(t)
    # Curved path (sideways bow) + reduced forward distance -> less straight.
    x = distance * s
    y = curvature * np.sin(2.0 * np.pi * s)  # extra wobble -> low straightness
    wrist_xy = np.stack([x, y], axis=1)

    # Sluggish grasp: small aperture range (hand barely opens).
    aperture = 0.045 * (1.0 - s) + 0.035

    rng = np.random.default_rng(seed)
    lm = _build_landmarks(n_frames, wrist_xy, aperture, jitter_std=jitter_std, rng=rng)
    return HandTrajectory(landmarks=lm, fps=fps, label=label)
