"""Image quality analysis utilities."""

import cv2
import numpy as np
from typing import Dict, Tuple
from PIL import Image
from loguru import logger


class QualityAnalyzer:
    """Analyze image quality for preprocessing validation."""
    
    def __init__(
        self,
        min_height: int = 100,
        min_width: int = 100,
        min_brightness: float = 30,
        max_brightness: float = 225,
        blur_threshold: float = 50,
    ):
        """
        Initialize quality analyzer.
        
        Args:
            min_height: Minimum image height in pixels
            min_width: Minimum image width in pixels
            min_brightness: Minimum average brightness (0-255)
            max_brightness: Maximum average brightness (0-255)
            blur_threshold: Blur detection threshold (Laplacian variance)
        """
        self.min_height = min_height
        self.min_width = min_width
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.blur_threshold = blur_threshold
    
    def analyze(self, image_path: str) -> Dict[str, float]:
        """
        Perform comprehensive quality analysis on image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with quality metrics
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                logger.warning(f"Could not read image: {image_path}")
                return self._empty_result(image_path, "could_not_read")
            
            height, width = img.shape[:2]
            
            # Size check
            if height < self.min_height or width < self.min_width:
                return self._empty_result(
                    image_path,
                    f"image_too_small:{width}x{height}"
                )
            
            # Calculate quality metrics
            results = {
                "image_path": image_path,
                "width": width,
                "height": height,
                "aspect_ratio": width / height if height > 0 else 0,
            }
            
            # Brightness analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            results["brightness"] = brightness
            
            if brightness < self.min_brightness or brightness > self.max_brightness:
                results["quality_flag"] = f"bad_brightness:{brightness:.1f}"
                results["quality_score"] = 0.0
                return results
            
            # Blur detection
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            results["blur_score"] = laplacian_var
            
            if laplacian_var < self.blur_threshold:
                results["quality_flag"] = f"blurry:{laplacian_var:.1f}"
                results["quality_score"] = 0.0
                return results
            
            # Contrast analysis
            contrast = np.std(gray)
            results["contrast"] = contrast
            
            # Color richness (for RGB images)
            if len(img.shape) == 3:
                color_variety = self._calculate_color_variety(img)
                results["color_variety"] = color_variety
            else:
                results["color_variety"] = 0.0
            
            # Calculate composite quality score (0-100)
            quality_score = self._calculate_quality_score(results)
            results["quality_score"] = quality_score
            results["quality_flag"] = "pass"
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            return self._empty_result(image_path, f"error:{str(e)}")
    
    def _calculate_color_variety(self, img: np.ndarray) -> float:
        """Calculate color variety in image."""
        try:
            # Reshape image to list of pixel colors
            pixels = img.reshape(-1, img.shape[-1])
            
            # Calculate unique colors (approximate)
            unique_colors = len(np.unique(pixels, axis=0))
            total_pixels = pixels.shape[0]
            
            # Normalize to 0-100
            color_variety = min(100.0, (unique_colors / total_pixels) * 100)
            return color_variety
        except Exception:
            return 0.0
    
    def _calculate_quality_score(self, results: Dict) -> float:
        """
        Calculate composite quality score.
        
        Args:
            results: Dictionary with quality metrics
            
        Returns:
            Quality score (0-100)
        """
        score = 100.0
        
        # Normalize brightness (expect 50-200)
        brightness = results.get("brightness", 128)
        brightness_score = 100 - abs(brightness - 128) / 2
        brightness_score = max(0, min(100, brightness_score))
        
        # Blur score (threshold is 50, normalize to 0-100)
        blur_score = results.get("blur_score", 0)
        blur_normalized = min(100, (blur_score / 100) * 100)
        
        # Contrast score (expect 30-100, normalize)
        contrast = results.get("contrast", 0)
        contrast_normalized = min(100, (contrast / 50) * 100)
        
        # Weighted combination
        score = (
            brightness_score * 0.3 +
            blur_normalized * 0.4 +
            contrast_normalized * 0.3
        )
        
        return float(score)
    
    def _empty_result(self, image_path: str, reason: str) -> Dict:
        """Create an empty quality result."""
        return {
            "image_path": image_path,
            "width": 0,
            "height": 0,
            "aspect_ratio": 0,
            "brightness": 0,
            "blur_score": 0,
            "contrast": 0,
            "color_variety": 0,
            "quality_score": 0.0,
            "quality_flag": reason,
        }
    
    def batch_analyze(self, image_paths: list) -> list:
        """
        Analyze multiple images.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of quality analysis results
        """
        results = []
        for i, path in enumerate(image_paths):
            if i % 50 == 0:
                logger.info(f"Analyzing image quality {i+1}/{len(image_paths)}")
            result = self.analyze(path)
            results.append(result)
        return results
