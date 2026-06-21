"""MediaPipe Hands 21-landmark schema.

This is the *single source of truth* for landmark indices shared between:
  - the video tracker (``src/ai/tracking``) using MediaPipe Hands, and
  - the Blender 3D reference hand (armature bones placed at these points).

Keeping the indices identical on both sides lets us feed the Blender reference
trajectory and the patient video trajectory through the *same* metric functions
in this package, so the split-screen comparison is mathematically consistent.
"""
from __future__ import annotations

from typing import Final

# Canonical MediaPipe Hands landmark indices (0..20).
WRIST: Final[int] = 0

# Thumb
THUMB_CMC: Final[int] = 1
THUMB_MCP: Final[int] = 2
THUMB_IP: Final[int] = 3
THUMB_TIP: Final[int] = 4

# Index finger
INDEX_MCP: Final[int] = 5
INDEX_PIP: Final[int] = 6
INDEX_DIP: Final[int] = 7
INDEX_TIP: Final[int] = 8

# Middle finger
MIDDLE_MCP: Final[int] = 9
MIDDLE_PIP: Final[int] = 10
MIDDLE_DIP: Final[int] = 11
MIDDLE_TIP: Final[int] = 12

# Ring finger
RING_MCP: Final[int] = 13
RING_PIP: Final[int] = 14
RING_DIP: Final[int] = 15
RING_TIP: Final[int] = 16

# Pinky
PINKY_MCP: Final[int] = 17
PINKY_PIP: Final[int] = 18
PINKY_DIP: Final[int] = 19
PINKY_TIP: Final[int] = 20

N_LANDMARKS: Final[int] = 21

LANDMARK_NAMES: Final[tuple[str, ...]] = (
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
)

# Convenience groupings used by the metric functions.
FINGER_TIPS: Final[tuple[int, ...]] = (THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)
FINGER_MCPS: Final[tuple[int, ...]] = (INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)
# The two landmarks whose distance defines the "grasp aperture".
GRASP_APERTURE_PAIR: Final[tuple[int, int]] = (THUMB_TIP, INDEX_TIP)
