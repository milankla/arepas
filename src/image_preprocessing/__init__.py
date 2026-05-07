"""
Image preprocessing module for building detection.

This module provides:
- Building detection using GroundingDINO (IDEA-Research/grounding-dino-tiny)
"""

from .detector_base import BaseDetector
from .grounding_dino_detector import GroundingDINODetector

__all__ = [
    "BaseDetector",
    "GroundingDINODetector",
]
