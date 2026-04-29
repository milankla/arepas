"""
Image preprocessing module for building detection and segmentation.

This module provides:
- Building detection using Faster R-CNN (PyTorch/Torchvision) for precise bounding boxes
- Building detection using Meta SAM2 (Segment Anything Model 2)
- Simplified pipeline for cropped image extraction
"""

from .detector_base import BaseDetector
from .mask_rcnn_detector import MaskRCNNDetector
from .sam2_detector import SAM2Detector
from .simplified_pipeline import SimplifiedPipeline

__all__ = [
    "BaseDetector",
    "MaskRCNNDetector",
    "SAM2Detector",
    "SimplifiedPipeline",
]
