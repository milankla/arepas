"""Meta SAM (Segment Anything Model) for building segmentation."""

import time
from typing import Tuple, List, Optional
import numpy as np
from PIL import Image
from loguru import logger

from .detector_base import BaseDetector, DetectionResult


class SAM2Detector(BaseDetector):
    """
    Building detector using Meta's Segment Anything Model (SAM).
    
    Uses automatic segmentation to detect and extract building regions.
    Selects the largest segment (assumed to be the main building).
    """
    
    def __init__(
        self,
        model_name: str = "sam",
        device: str = "cpu",
        confidence_threshold: float = 0.5,
        min_building_area_ratio: float = 0.05,
        max_building_area_ratio: float = 0.95,
    ):
        """
        Initialize SAM detector.
        
        Args:
            model_name: Name for this detector
            device: Device to use ("cpu" or "cuda")
            confidence_threshold: Confidence threshold for detections
            min_building_area_ratio: Minimum building size (% of image)
            max_building_area_ratio: Maximum building size (% of image)
        """
        super().__init__(model_name, device)
        self.display_name = "SAM (Building Segmentation)"
        self.confidence_threshold = confidence_threshold
        self.min_building_area_ratio = min_building_area_ratio
        self.max_building_area_ratio = max_building_area_ratio
        self.predictor = None
        self.load_model()
    
    def load_model(self):
        """Load Meta SAM model."""
        try:
            import torch
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
            
            logger.info("Loading SAM (Segment Anything Model)...")
            
            device = "cuda" if self.device == "cuda" else "cpu"
            
            # Load SAM model (base model)
            # Note: You may need to download the model weights first
            # Run: wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
            sam = sam_model_registry["vit_b"](checkpoint="sam_vit_b_01ec64.pth")
            sam.to(device=device)
            
            # Create automatic mask generator
            self.predictor = SamAutomaticMaskGenerator(sam)
            
            logger.info(f"✓ SAM loaded successfully on {self.device}")
            
        except ImportError as e:
            logger.error(
                f"SAM not installed. Install with: pip install git+https://github.com/facebookresearch/segment-anything.git"
            )
            raise
        except FileNotFoundError as e:
            logger.error(
                f"SAM model weights not found. Download with:\n"
                f"  wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading SAM: {e}")
            raise
    
    def detect(self, image_path: str) -> DetectionResult:
        """
        Detect buildings in image using SAM.
        
        Args:
            image_path: Path to image file
            
        Returns:
            DetectionResult with bounding boxes for main building
        """
        start_time = time.time()
        
        try:
            if self.predictor is None:
                raise RuntimeError("Model not loaded. Call load_model() first.")
            
            # Load image
            with Image.open(image_path) as img:
                image = np.array(img.convert("RGB"))
            
            img_height, img_width = image.shape[:2]
            img_area = img_height * img_width
            
            # Generate masks
            masks = self.predictor.generate(image)
            
            best_bbox = None
            best_confidence = 0.0
            best_mask = None
            
            if len(masks) > 0:
                # Sort masks by area (largest first)
                masks_sorted = sorted(masks, key=lambda x: x.get('area', 0), reverse=True)
                
                # Image center for centrality heuristic
                img_center = np.array([img_width / 2.0, img_height / 2.0])
                img_diag = np.sqrt(img_width ** 2 + img_height ** 2)
                
                for mask_data in masks_sorted:
                    mask = mask_data.get('segmentation')
                    area = mask_data.get('area', 0)
                    area_ratio = area / img_area if img_area > 0 else 0
                    
                    # Size constraints
                    if area_ratio < self.min_building_area_ratio:
                        continue
                    if area_ratio > self.max_building_area_ratio:
                        continue
                    
                    # Get bounding box from mask if available, else infer from mask
                    bbox_data = mask_data.get('bbox')
                    if bbox_data is not None and len(bbox_data) == 4:
                        # SAM bbox format: (x, y, w, h)
                        x, y, w, h = bbox_data
                        cmin, rmin = int(x), int(y)
                        cmax, rmax = int(x + w), int(y + h)
                    else:
                        # Infer from mask
                        rows = np.any(mask, axis=1)
                        cols = np.any(mask, axis=0)
                        if not (rows.any() and cols.any()):
                            continue
                        rmin, rmax = np.where(rows)[0][[0, -1]]
                        cmin, cmax = np.where(cols)[0][[0, -1]]
                    
                    bbox = (cmin, rmin, cmax, rmax)
                    
                    # Compute a heuristic confidence using predicted_iou if available
                    predicted_iou = mask_data.get('predicted_iou') or mask_data.get('stability_score') or 0
                    confidence = float(predicted_iou) if predicted_iou is not None else float(area_ratio)
                    
                    # Use centrality as tie-breaker: closer to image center is preferred
                    bbox_center = np.array([(cmin + cmax) / 2.0, (rmin + rmax) / 2.0])
                    center_dist = np.linalg.norm(bbox_center - img_center) / img_diag
                    center_score = 1.0 - center_dist
                    
                    # Final score: prioritize predicted IoU, then centrality
                    score = confidence * 0.8 + center_score * 0.2
                    
                    if score > best_confidence:
                        best_confidence = score
                        best_bbox = bbox
                        best_mask = mask

            # Refine mask to largest connected component to avoid large non-building regions
            if best_mask is not None:
                try:
                    import cv2

                    # Convert to uint8 (0/255) for connected components
                    mask_uint8 = (best_mask.astype('uint8') * 255)
                    num_labels, labels = cv2.connectedComponents(mask_uint8)

                    # Find largest component excluding background (label 0)
                    if num_labels > 1:
                        largest_label = 1
                        largest_size = 0
                        for label in range(1, num_labels):
                            size = int((labels == label).sum())
                            if size > largest_size:
                                largest_size = size
                                largest_label = label

                        refined_mask = (labels == largest_label)
                        best_mask = refined_mask

                        # Recompute bbox from refined mask
                        rows = np.any(best_mask, axis=1)
                        cols = np.any(best_mask, axis=0)
                        if rows.any() and cols.any():
                            rmin, rmax = np.where(rows)[0][[0, -1]]
                            cmin, cmax = np.where(cols)[0][[0, -1]]
                            best_bbox = (int(cmin), int(rmin), int(cmax), int(rmax))
                except Exception:
                    # If cv2 isn't available or fails, skip refinement.
                    pass

            detected = best_bbox is not None
            processing_time = time.time() - start_time

            if detected:
                logger.debug(
                    f"SAM detected building in {image_path} "
                    f"(confidence: {best_confidence:.2%}, {processing_time:.3f}s)"
                )
            else:
                logger.debug(f"SAM detected no buildings in {image_path}")

            return DetectionResult(
                image_path=image_path,
                detected=detected,
                bounding_boxes=[best_bbox] if best_bbox is not None else [],
                confidence_scores=[best_confidence] if best_bbox is not None else [],
                masks=[best_mask] if best_mask is not None else [],
                processing_time=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Error detecting in {image_path}: {e}")
            processing_time = time.time() - start_time
            return DetectionResult(
                image_path=image_path,
                detected=False,
                bounding_boxes=[],
                confidence_scores=[],
                processing_time=processing_time,
                error=str(e),
            )
    
    def extract_building(
        self,
        image_path: str,
        bbox: Tuple[int, int, int, int],
        mask: Optional[np.ndarray] = None,
    ) -> Image.Image:
        """
        Extract building region using bounding box.
        
        Args:
            image_path: Path to image
            bbox: Bounding box (x1, y1, x2, y2)
            mask: Optional binary mask (same size as image) for refining the crop.
            
        Returns:
            Cropped PIL Image
        """
        try:
            with Image.open(image_path) as img:
                x1, y1, x2, y2 = bbox
                # Add padding to capture more context (10% on each side)
                width = x2 - x1
                height = y2 - y1
                padding_x = int(width * 0.1)
                padding_y = int(height * 0.1)
                
                x1 = max(0, x1 - padding_x)
                y1 = max(0, y1 - padding_y)
                x2 = min(img.width, x2 + padding_x)
                y2 = min(img.height, y2 + padding_y)
                
                # Crop image
                cropped = img.crop((x1, y1, x2, y2))

                # If mask is provided, apply it to remove background and keep only the building.
                if mask is not None:
                    try:
                        # Ensure mask is boolean / uint8 and crop it consistently
                        mask_arr = np.asarray(mask, dtype=np.uint8)
                        mask_img = Image.fromarray((mask_arr * 255).astype('uint8'), mode='L')
                        mask_crop = mask_img.crop((x1, y1, x2, y2))

                        # Composite over white background to avoid alpha artifacts in JPG
                        cropped_rgba = cropped.convert('RGBA')
                        cropped_rgba.putalpha(mask_crop)
                        background = Image.new('RGBA', cropped_rgba.size, (255, 255, 255, 255))
                        composited = Image.alpha_composite(background, cropped_rgba)
                        return composited.convert('RGB')
                    except Exception:
                        # Fallback to standard crop if mask processing fails
                        pass

                return cropped
        except Exception as e:
            logger.error(f"Error extracting building from {image_path}: {e}")
            raise
