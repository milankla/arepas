"""Main preprocessing pipeline orchestrator."""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import asdict
from loguru import logger

from .detector_base import BaseDetector
from .quality_analyzer import QualityAnalyzer
from .image_aligner import ImageAligner


class PreprocessingPipeline:
    """Orchestrates full image preprocessing pipeline."""
    
    def __init__(
        self,
        detector: BaseDetector,
        output_dir: str,
        quality_analyzer: QualityAnalyzer = None,
        image_aligner: ImageAligner = None,
    ):
        """
        Initialize preprocessing pipeline.
        
        Args:
            detector: Building detector instance
            output_dir: Directory for preprocessed images and metadata
            quality_analyzer: Quality analyzer instance
            image_aligner: Image aligner instance
        """
        self.detector = detector
        self.output_dir = output_dir
        self.quality_analyzer = quality_analyzer or QualityAnalyzer()
        self.image_aligner = image_aligner or ImageAligner()
        
        # Create output directories
        self.cropped_dir = os.path.join(output_dir, "cropped")
        self.aligned_dir = os.path.join(output_dir, "aligned")
        self.rejected_dir = os.path.join(output_dir, "rejected")
        
        for dir_path in [self.cropped_dir, self.aligned_dir, self.rejected_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        self.metadata = []
        self.start_time = None
        self.end_time = None
    
    def process_images(self, image_paths: List[str]) -> Dict:
        """
        Process images through full pipeline.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            Summary statistics
        """
        self.start_time = time.time()
        total = len(image_paths)
        
        logger.info(f"Starting preprocessing pipeline for {total} images")
        logger.info(f"Detector: {self.detector.model_name}")
        logger.info(f"Output directory: {self.output_dir}")
        
        stats = {
            "total": total,
            "detected": 0,
            "passed_quality": 0,
            "aligned": 0,
            "rejected": 0,
            "failed": 0,
        }
        
        for i, image_path in enumerate(image_paths):
            if (i + 1) % 10 == 0 or i == 0:
                logger.info(f"Processing {i+1}/{total} images")
            
            try:
                result = self._process_single_image(image_path)
                
                if result.get("status") == "success":
                    stats["detected"] += 1
                    if result.get("quality_flag") == "pass":
                        stats["passed_quality"] += 1
                        if result.get("aligned"):
                            stats["aligned"] += 1
                    else:
                        stats["rejected"] += 1
                else:
                    stats["rejected"] += 1
                
                self.metadata.append(result)
                
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                stats["failed"] += 1
                self.metadata.append({
                    "source_image": image_path,
                    "status": "error",
                    "error": str(e),
                })
        
        self.end_time = time.time()
        stats["processing_time_seconds"] = self.end_time - self.start_time
        
        return stats
    
    def _process_single_image(self, image_path: str) -> Dict:
        """
        Process a single image through the pipeline.
        
        Args:
            image_path: Path to image
            
        Returns:
            Metadata for this image
        """
        metadata = {
            "source_image": image_path,
            "detector": self.detector.model_name,
            "timestamp": time.time(),
        }
        
        # Step 1: Detection
        detection_result = self.detector.detect(image_path)
        metadata["detected"] = detection_result.detected
        metadata["detection_time"] = detection_result.processing_time
        metadata["detection_error"] = detection_result.error
        
        if not detection_result.detected:
            metadata["status"] = "no_detection"
            return metadata
        
        metadata["bounding_boxes"] = detection_result.bounding_boxes
        metadata["confidence_scores"] = detection_result.confidence_scores
        
        # Use the highest confidence detection
        best_idx = 0
        if detection_result.confidence_scores:
            best_idx = detection_result.confidence_scores.index(
                max(detection_result.confidence_scores)
            )
        
        bbox = detection_result.bounding_boxes[best_idx]
        confidence = detection_result.confidence_scores[best_idx]
        
        # Step 2: Extract building
        try:
            cropped_image = self.detector.extract_building(image_path, bbox)
            filename_base = Path(image_path).stem
            cropped_path = os.path.join(self.cropped_dir, f"{filename_base}_cropped.jpg")
            cropped_image.save(cropped_path, quality=95)
            metadata["cropped_image"] = cropped_path
        except Exception as e:
            logger.error(f"Error extracting building: {e}")
            metadata["status"] = "extraction_error"
            return metadata
        
        # Step 3: Quality Analysis
        quality_result = self.quality_analyzer.analyze(cropped_path)
        metadata.update(quality_result)
        
        if quality_result.get("quality_flag") != "pass":
            metadata["status"] = "quality_rejected"
            # Move to rejected folder
            try:
                import shutil
                rejected_path = os.path.join(
                    self.rejected_dir,
                    f"{filename_base}_rejected.jpg"
                )
                shutil.move(cropped_path, rejected_path)
                metadata["rejected_image"] = rejected_path
            except Exception as e:
                logger.warning(f"Could not move rejected image: {e}")
            return metadata
        
        # Step 4: Image Alignment
        try:
            aligned_path = os.path.join(self.aligned_dir, f"{filename_base}_aligned.jpg")
            self.image_aligner.align(cropped_path, aligned_path)
            metadata["aligned_image"] = aligned_path
            metadata["aligned"] = True
        except Exception as e:
            logger.error(f"Error aligning image: {e}")
            metadata["aligned"] = False
            metadata["alignment_error"] = str(e)
        
        metadata["status"] = "success"
        return metadata
    
    def save_metadata(self, output_path: str = None):
        """
        Save metadata to JSON file.
        
        Args:
            output_path: Path to save metadata JSON
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, "metadata.json")
        
        with open(output_path, "w") as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.info(f"Metadata saved to {output_path}")
    
    def get_summary(self) -> Dict:
        """Get pipeline execution summary."""
        if not self.metadata:
            return {}
        
        successful = sum(1 for m in self.metadata if m.get("status") == "success")
        detected = sum(1 for m in self.metadata if m.get("detected", False))
        quality_pass = sum(1 for m in self.metadata if m.get("quality_flag") == "pass")
        aligned = sum(1 for m in self.metadata if m.get("aligned", False))
        
        return {
            "total_images": len(self.metadata),
            "detection_rate": f"{(detected/len(self.metadata)*100):.1f}%",
            "quality_pass_rate": f"{(quality_pass/detected*100) if detected > 0 else 0:.1f}%",
            "alignment_rate": f"{(aligned/len(self.metadata)*100):.1f}%",
            "final_success_rate": f"{(successful/len(self.metadata)*100):.1f}%",
            "processing_time_seconds": self.end_time - self.start_time if self.end_time else 0,
        }
