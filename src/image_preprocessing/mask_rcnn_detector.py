"""PyTorch-based Faster R-CNN detector for precise building detection.

This detector uses torchvision's pre-trained Faster R-CNN model (trained on COCO)
to detect buildings/houses in images and return tight bounding boxes.

The model provides:
- Precise instance detection with tight bounding boxes
- COCO pre-training for general object detection
- Compatible with existing PyTorch/torchvision dependencies
"""

import time
from typing import Optional, List
import numpy as np
import torch
from PIL import Image
from loguru import logger

from .detector_base import BaseDetector, DetectionResult


class MaskRCNNDetector(BaseDetector):
    """Building detector using PyTorch Faster R-CNN."""

    def __init__(
        self,
        model_name: str = "mask_rcnn",
        device: str = "cpu",
        confidence_threshold: float = 0.5,
        min_area_ratio: float = 0.01,
        max_area_ratio: float = 1.0,
    ):
        """
        Initialize Faster R-CNN detector.

        Args:
            model_name: Name for this detector instance.
            device: Device to use ("cpu" or "cuda").
            confidence_threshold: Minimum confidence score for predictions (0-1).
            min_area_ratio: Minimum building area as ratio of image (0-1).
            max_area_ratio: Maximum building area as ratio of image (0-1).
        """
        super().__init__(model_name, device)
        self.display_name = "Faster R-CNN (PyTorch/Torchvision)"
        self.confidence_threshold = confidence_threshold
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.model = None
        self.load_model()

    def load_model(self):
        """Load Faster R-CNN model from torchvision."""
        try:
            import torchvision
            from torchvision.models.detection import fasterrcnn_resnet50_fpn

            logger.info("Loading Faster R-CNN (PyTorch/Torchvision)...")

            # Load pre-trained model
            self.model = fasterrcnn_resnet50_fpn(
                weights='DEFAULT',
                box_detections_per_img=100,
                score_thresh=self.confidence_threshold,
            )

            # Set device
            device = torch.device("cuda" if self.device == "cuda" else "cpu")
            self.model = self.model.to(device)
            self.model.eval()

            logger.info(f"✓ Faster R-CNN loaded successfully on {device}")

        except ImportError as e:
            logger.error(f"Torchvision not installed. Install with: pip install torchvision")
            raise
        except Exception as e:
            logger.error(f"Error loading Faster R-CNN: {e}")
            raise

    def detect(self, image_path: str) -> DetectionResult:
        """
        Detect buildings in an image using Faster R-CNN.

        Args:
            image_path: Path to the image file

        Returns:
            DetectionResult with bounding boxes and confidence scores
        """
        try:
            start_time = time.time()

            # Load image
            image = Image.open(image_path).convert("RGB")
            image_tensor = torch.as_tensor(
                np.array(image).transpose(2, 0, 1), 
                dtype=torch.float32
            )
            
            height, width = image.size[1], image.size[0]
            image_area = height * width

            # Run inference
            device = torch.device("cuda" if self.device == "cuda" else "cpu")
            image_tensor = image_tensor.to(device)
            
            with torch.no_grad():
                predictions = self.model([image_tensor])
            
            # Extract predictions
            boxes = predictions[0]["boxes"].cpu().numpy()
            scores = predictions[0]["scores"].cpu().numpy()

            # Filter by confidence threshold and area constraints
            bounding_boxes = []
            confidence_scores = []

            for box, score in zip(boxes, scores):
                if score < self.confidence_threshold:
                    continue

                x1, y1, x2, y2 = map(int, box)
                box_area = (x2 - x1) * (y2 - y1)
                area_ratio = box_area / image_area

                # Check area constraints
                if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
                    continue

                bounding_boxes.append((x1, y1, x2, y2))
                confidence_scores.append(float(score))

            processing_time = time.time() - start_time

            detected = len(bounding_boxes) > 0

            result = DetectionResult(
                image_path=image_path,
                detected=detected,
                bounding_boxes=bounding_boxes,
                confidence_scores=confidence_scores,
                processing_time=processing_time,
            )

            if detected:
                logger.info(
                    f"Detected {len(bounding_boxes)} object(s) in {image_path} "
                    f"(confidence: {confidence_scores[0]:.2f})"
                )
            else:
                logger.warning(f"No objects detected in {image_path}")

            return result

        except Exception as e:
            logger.error(f"Error detecting buildings in {image_path}: {e}")
            return DetectionResult(
                image_path=image_path,
                detected=False,
                bounding_boxes=[],
                confidence_scores=[],
                error=str(e),
            )

    def detect_largest_building(self, image_path: str) -> DetectionResult:
        """
        Detect and return only the largest object in the image.
        
        Useful for images with a single main building/house.

        Args:
            image_path: Path to the image file

        Returns:
            DetectionResult with the largest bounding box
        """
        result = self.detect(image_path)

        if not result.detected or not result.bounding_boxes:
            return result

        # Find largest bounding box by area
        largest_idx = 0
        largest_area = 0

        for idx, (x1, y1, x2, y2) in enumerate(result.bounding_boxes):
            area = (x2 - x1) * (y2 - y1)
            if area > largest_area:
                largest_area = area
                largest_idx = idx

        # Keep only the largest
        result.bounding_boxes = [result.bounding_boxes[largest_idx]]
        result.confidence_scores = [result.confidence_scores[largest_idx]]

        logger.info(
            f"Selected largest detection: area={largest_area}, "
            f"confidence={result.confidence_scores[0]:.2f}"
        )

        return result

    def extract_building(
        self, 
        image_path: str, 
        bbox: tuple = None,
        mask = None
    ) -> Image.Image:
        """
        Extract building region from image using bounding box.

        Args:
            image_path: Path to the image
            bbox: Bounding box (x1, y1, x2, y2). If None, uses largest detected building.
            mask: Optional binary mask (not used for Faster R-CNN)

        Returns:
            Cropped PIL Image of the building region
        """
        try:
            image = Image.open(image_path).convert("RGB")

            # If no bbox provided, detect the largest building
            if bbox is None:
                result = self.detect_largest_building(image_path)
                if not result.bounding_boxes:
                    logger.warning(f"No building detected in {image_path}")
                    return image
                bbox = result.bounding_boxes[0]

            x1, y1, x2, y2 = bbox
            
            # Crop the image
            cropped = image.crop((x1, y1, x2, y2))
            logger.info(f"Extracted building region: {bbox}")

            return cropped

        except Exception as e:
            logger.error(f"Error extracting building from {image_path}: {e}")
            return Image.open(image_path).convert("RGB")
