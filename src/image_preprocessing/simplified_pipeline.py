"""Simplified preprocessing pipeline for building crop extraction."""

import os
import json
import time
from pathlib import Path
from typing import Dict, List
from dataclasses import asdict
from loguru import logger

from .detector_base import BaseDetector


class SimplifiedPipeline:
    """Simplified pipeline that only produces cropped building images."""
    
    def __init__(
        self,
        detector: BaseDetector,
        output_dir: str,
    ):
        """
        Initialize simplified pipeline.
        
        Args:
            detector: Building detector instance
            output_dir: Directory for cropped images
        """
        self.detector = detector
        self.output_dir = output_dir
        self.cropped_dir = os.path.join(output_dir, "cropped")
        
        # Create output directory
        os.makedirs(self.cropped_dir, exist_ok=True)
        
        self.metadata = []
        self.start_time = None
        self.end_time = None
    
    def process_images(self, image_paths: List[str]) -> Dict:
        """
        Process images through pipeline.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            Summary statistics
        """
        self.start_time = time.time()
        total = len(image_paths)
        
        logger.info(f"Starting simplified pipeline for {total} images")
        logger.info(f"Detector: {self.detector.model_name}")
        logger.info(f"Output directory: {self.output_dir}")
        
        stats = {
            "total": total,
            "detected": 0,
            "cropped": 0,
            "failed": 0,
        }
        
        for i, image_path in enumerate(image_paths):
            if (i + 1) % 50 == 0 or i == 0:
                logger.info(f"Processing {i+1}/{total} images")
            
            try:
                result = self._process_single_image(image_path)
                
                if result.get("status") == "success":
                    stats["detected"] += 1
                    stats["cropped"] += 1
                    self.metadata.append(result)
                else:
                    # Log details on why detection/crop failed.
                    err = result.get("error") or result.get("message")
                    if err:
                        logger.warning(f"Failed to process {image_path}: {err}")

                        # Stop early on critical authentication/API errors
                        if "API key" in err or "Forbidden" in err or "authentication" in err.lower():
                            logger.error(f"Stopping early due to authentication/API failure: {err}")
                            stats["failed"] += (total - i)
                            break

                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                stats["failed"] += 1
        
        self.end_time = time.time()
        stats["processing_time"] = self.end_time - self.start_time
        
        logger.info(f"\n✓ Processing complete")
        logger.info(f"  Total: {stats['total']}")
        logger.info(f"  Detected: {stats['detected']}")
        logger.info(f"  Cropped: {stats['cropped']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Time: {stats['processing_time']:.1f}s")
        
        return stats
    
    def _process_single_image(self, image_path: str) -> Dict:
        """Process a single image through detection and cropping."""
        try:
            # Detect building
            detection = self.detector.detect(image_path)

            if detection.error:
                return {"status": "error", "image_path": image_path, "error": detection.error}

            if not detection.detected or len(detection.bounding_boxes) == 0:
                return {"status": "no_detection", "image_path": image_path}
            
            # Extract and save cropped image
            bbox = detection.bounding_boxes[0]
            confidence = detection.confidence_scores[0]
            mask = None
            if detection.masks and len(detection.masks) > 0:
                mask = detection.masks[0]
            
            try:
                cropped_img = self.detector.extract_building(image_path, bbox, mask=mask)
            except Exception as e:
                logger.warning(f"Failed to extract building from {image_path}: {e}")
                return {"status": "extraction_failed", "image_path": image_path}
            
            # Save cropped image
            filename = Path(image_path).stem
            cropped_path = os.path.join(self.cropped_dir, f"{filename}_cropped.jpg")
            cropped_img.save(cropped_path, quality=95)
            
            return {
                "status": "success",
                "image_path": image_path,
                "cropped_image": cropped_path,
                "bbox": bbox,
                "confidence": float(confidence),
                "processing_time": detection.processing_time,
            }
            
        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            return {"status": "error", "image_path": image_path, "error": str(e)}
    
    def save_metadata(self):
        """Save metadata to JSON file."""
        metadata_path = os.path.join(self.output_dir, "metadata.json")
        
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.info(f"✓ Metadata saved to {metadata_path}")
