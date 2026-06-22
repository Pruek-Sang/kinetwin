"""Pydantic response models for the /analyze report (mirrors ai.pipeline)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HandMetrics(BaseModel):
    speed: float = Field(..., description="normalised speed sub-score 0..100")
    accuracy: float = Field(..., description="path-straightness sub-score 0..100")
    quality: float = Field(..., description="smoothness sub-score 0..100")
    composite: float = Field(..., description="weighted dexterity composite 0..100")
    raw: dict = Field(..., description="raw metric values (mean_speed, straightness, ...)")


class AnalyzeReport(BaseModel):
    metrics: dict[str, HandMetrics] = Field(..., description="{'left': ..., 'right': ...}")
    dominant_hand: str
    score_gap: float
    learned_non_use: dict
    weights: dict
    learned_non_use_gap_threshold: float
    note: Optional[str] = None
