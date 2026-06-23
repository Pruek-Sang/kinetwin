"""Composite dexterity scoring + Learned Non-Use detection.

Each raw metric is normalised to a 0..100 sub-score against a *reference
baseline* (the ideal/"normal" hand -- typically the Blender reference or the
patient's own unaffected side). The three sub-scores follow the hackathon
brief exactly:

* **Speed**    -- from :func:`wrist_mean_speed`
* **Accuracy** -- from :func:`path_straightness`
* **Quality**  -- from :func:`smoothness_index`

The composite is a fixed-weight mean of the three (weights sum to 1).

:func:`compare_hands` then contrasts the two hands and flags a suspected
**Learned Non-Use** side: the hand whose composite is markedly lower (gap >=
``learned_non_use_gap`` points) is the candidate "forgotten" side.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .accuracy import path_straightness
from .quality import MIN_JERK_NC, dimensionless_jerk, smoothness_index, velocity_peaks
from .speed import wrist_mean_speed
from .trajectory import HandTrajectory

# Weights for the composite dexterity score (sum to 1.0).
DEFAULT_WEIGHTS: dict[str, float] = {"speed": 0.20, "accuracy": 0.10, "quality": 0.70}

#: Soft margin applied during scoring so real human movement (which has natural
#: variation and can never match a synthetic ideal) is not over-penalised.
#: Quality: ``baseline_jerk * QUALITY_MARGIN / patient_jerk`` -- a patient can
#: be up to MARGIN× jerkier than baseline and still score 100.
QUALITY_MARGIN: float = 1.5
SPEED_MARGIN: float = 1.5

# Gap (in 0..100 points) above which the weaker hand is flagged as a
# Learned Non-Use candidate. ~20 points is a clinically noticeable difference.
DEFAULT_LEARNED_NON_USE_GAP: float = 20.0


@dataclass(frozen=True)
class MetricBreakdown:
    """Normalised sub-scores in 0..100 plus the raw values behind them."""

    speed: float
    accuracy: float
    quality: float
    composite: float
    raw: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class HandComparison:
    """Result of comparing the left and right hand of one patient."""

    dominant_label: str
    learned_non_use_label: Optional[str]
    learned_non_use_flag: bool
    gap: float
    left: MetricBreakdown
    right: MetricBreakdown


# --------------------------------------------------------------------- helpers
def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def raw_metrics(traj: HandTrajectory) -> dict[str, float]:
    """Collect the raw, un-normalised metrics for one hand.

    ``dimensionless_jerk`` (lower = smoother) is used for scoring; the
    ``smoothness_index`` (higher = smoother) is kept for display only.
    """
    return {
        "mean_speed": wrist_mean_speed(traj),
        "straightness": path_straightness(traj),
        "dimensionless_jerk": dimensionless_jerk(traj),
        "smoothness_index": smoothness_index(traj),
        "velocity_peaks": float(velocity_peaks(traj)),
    }


@dataclass(frozen=True)
class ReferenceBaseline:
    """The "normal" reference values used to normalise sub-scores.

    Sub-scores are ``clip(value / baseline, 0, 1) * 100`` for higher-is-better
    metrics (speed) and for the dimensionless jerk we invert the ratio
    (``baseline / value``) since lower jerk is smoother/better. Straightness is
    already bounded in ``(0, 1]`` and is mapped directly.
    """

    mean_speed: float
    dimensionless_jerk: float

    @classmethod
    def from_trajectory(cls, ref: HandTrajectory) -> "ReferenceBaseline":
        """Build a baseline directly from the ideal/reference trajectory."""
        return cls(
            mean_speed=wrist_mean_speed(ref),
            dimensionless_jerk=dimensionless_jerk(ref),
        )


def score_hand(
    traj: HandTrajectory,
    baseline: ReferenceBaseline,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
) -> MetricBreakdown:
    """Normalise raw metrics to 0..100 and combine into a composite."""
    raw = raw_metrics(traj)

    # Speed: higher is better (softened so real movement isn't over-penalised).
    if baseline.mean_speed > 0:
        speed_score = _clip01(raw["mean_speed"] * SPEED_MARGIN / baseline.mean_speed) * 100.0
    else:
        speed_score = 0.0

    # Accuracy: straightness already in (0, 1] -> map directly.
    accuracy_score = _clip01(raw["straightness"]) * 100.0

    # Quality: dimensionless jerk, lower = better -> invert ratio with soft margin.
    nc = raw["dimensionless_jerk"]
    if baseline.dimensionless_jerk > 0 and math.isfinite(nc) and nc > 0:
        quality_score = _clip01(baseline.dimensionless_jerk * QUALITY_MARGIN / nc) * 100.0
    else:
        quality_score = 0.0

    composite = (
        weights["speed"] * speed_score
        + weights["accuracy"] * accuracy_score
        + weights["quality"] * quality_score
    )

    return MetricBreakdown(
        speed=speed_score,
        accuracy=accuracy_score,
        quality=quality_score,
        composite=composite,
        raw=raw,
    )


def compare_hands(
    left: HandTrajectory,
    right: HandTrajectory,
    baseline: ReferenceBaseline,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    learned_non_use_gap: float = DEFAULT_LEARNED_NON_USE_GAP,
) -> HandComparison:
    """Score both hands and flag a suspected Learned Non-Use side.

    The *dominant* (better-performing) hand is almost always the unaffected
    side; the *markedly weaker* hand is the Learned Non-Use candidate. The
    baseline used for normalisation should be the ideal reference (or the
    patient's unaffected side) so scores are absolute, not just relative.
    """
    left_score = score_hand(left, baseline, weights)
    right_score = score_hand(right, baseline, weights)

    if left_score.composite >= right_score.composite:
        dominant, weaker, dominant_label, weaker_label = left_score, right_score, "left", "right"
    else:
        dominant, weaker, dominant_label, weaker_label = right_score, left_score, "right", "left"

    gap = float(dominant.composite - weaker.composite)
    flag = gap >= learned_non_use_gap

    return HandComparison(
        dominant_label=dominant_label,
        learned_non_use_label=(weaker_label if flag else None),
        learned_non_use_flag=flag,
        gap=gap,
        left=left_score,
        right=right_score,
    )
