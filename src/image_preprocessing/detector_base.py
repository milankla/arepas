"""Base class for building detectors."""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from PIL import Image


@dataclass
class DetectionResult:
    """Result from building detection."""
    
    image_path: str
    detected: bool
    bounding_boxes: List[Tuple[int, int, int, int]]  # List of (x1, y1, x2, y2)
    confidence_scores: List[float]
    masks: List[Any] = None  # For instance segmentation
    processing_time: float = 0.0
    error: str = None


class BaseDetector(ABC):
    """Abstract base class for building detectors."""
    
    def __init__(self, model_name: str, device: str = "cpu"):
        """
        Initialize detector.
        
        Args:
            model_name: Name of the detector model
            device: Device to use ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.display_name = model_name  # Can be overridden for display purposes
        self.device = device
        self.model = None
        
    @abstractmethod
    def load_model(self):
        """Load the detection model."""
        pass
    
    @abstractmethod
    def detect(self, image_path: str) -> DetectionResult:
        """
        Detect buildings in an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            DetectionResult object with detection details
        """
        pass
    
    @abstractmethod
    def extract_building(
        self,
        image_path: str,
        bbox: Tuple[int, int, int, int],
        mask: Any = None,
    ) -> Image.Image:
        """
        Extract building region from image using bounding box.
        
        Args:
            image_path: Path to the image
            bbox: Bounding box (x1, y1, x2, y2)
            mask: Optional binary mask (same size as image) for refining the crop.
            
        Returns:
            Cropped PIL Image
        """
        pass
    
    def get_model_info(self) -> Dict[str, str]:
        """Get model information."""
        return {
            "model_name": self.model_name,
            "device": self.device,
        }
