"""Image alignment and standardization utilities."""

import cv2
import numpy as np
from PIL import Image
from loguru import logger
from typing import Tuple


class ImageAligner:
    """Align and standardize preprocessed images."""
    
    def __init__(
        self,
        target_height: int = 512,
        target_width: int = 512,
        maintain_aspect_ratio: bool = True,
    ):
        """
        Initialize image aligner.
        
        Args:
            target_height: Target image height
            target_width: Target image width
            maintain_aspect_ratio: Whether to maintain aspect ratio
        """
        self.target_height = target_height
        self.target_width = target_width
        self.maintain_aspect_ratio = maintain_aspect_ratio
    
    def align(self, image_path: str, output_path: str = None) -> Image.Image:
        """
        Align and standardize image.
        
        Args:
            image_path: Path to input image
            output_path: Optional path to save aligned image
            
        Returns:
            Aligned PIL Image
        """
        try:
            img = Image.open(image_path).convert("RGB")
            
            if self.maintain_aspect_ratio:
                aligned = self._resize_with_padding(img)
            else:
                aligned = img.resize(
                    (self.target_width, self.target_height),
                    Image.Resampling.LANCZOS
                )
            
            # Normalize color space
            aligned = self._normalize_colors(aligned)
            
            if output_path:
                aligned.save(output_path, quality=95)
                logger.debug(f"Saved aligned image to {output_path}")
            
            return aligned
            
        except Exception as e:
            logger.error(f"Error aligning image {image_path}: {e}")
            raise
    
    def _resize_with_padding(self, img: Image.Image) -> Image.Image:
        """
        Resize image while maintaining aspect ratio with padding.
        
        Args:
            img: PIL Image
            
        Returns:
            Resized PIL Image
        """
        img_w, img_h = img.size
        aspect_ratio = img_w / img_h
        target_ratio = self.target_width / self.target_height
        
        if aspect_ratio > target_ratio:
            # Image is wider, fit width
            new_w = self.target_width
            new_h = int(self.target_width / aspect_ratio)
        else:
            # Image is taller, fit height
            new_h = self.target_height
            new_w = int(self.target_height * aspect_ratio)
        
        # Resize image
        img_resized = img.resize(
            (new_w, new_h),
            Image.Resampling.LANCZOS
        )
        
        # Create canvas with padding
        canvas = Image.new("RGB", (self.target_width, self.target_height), (128, 128, 128))
        offset_x = (self.target_width - new_w) // 2
        offset_y = (self.target_height - new_h) // 2
        canvas.paste(img_resized, (offset_x, offset_y))
        
        return canvas
    
    def _normalize_colors(self, img: Image.Image) -> Image.Image:
        """
        Normalize image colors (histogram equalization).
        
        Args:
            img: PIL Image
            
        Returns:
            Normalized PIL Image
        """
        try:
            # Convert to numpy array
            img_array = np.array(img, dtype=np.uint8)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_equalized = clahe.apply(l_channel)
            
            lab_equalized = cv2.merge([l_equalized, a_channel, b_channel])
            rgb_equalized = cv2.cvtColor(lab_equalized, cv2.COLOR_LAB2RGB)
            
            return Image.fromarray(rgb_equalized, "RGB")
        except Exception as e:
            logger.warning(f"Color normalization failed: {e}, returning original image")
            return img
    
    def batch_align(self, image_paths: list, output_dir: str) -> list:
        """
        Align multiple images.
        
        Args:
            image_paths: List of input image paths
            output_dir: Directory to save aligned images
            
        Returns:
            List of output paths
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        output_paths = []
        for i, img_path in enumerate(image_paths):
            if i % 50 == 0:
                logger.info(f"Aligning image {i+1}/{len(image_paths)}")
            
            try:
                filename = os.path.basename(img_path)
                output_path = os.path.join(output_dir, filename)
                
                self.align(img_path, output_path)
                output_paths.append(output_path)
            except Exception as e:
                logger.error(f"Failed to align {img_path}: {e}")
                continue
        
        return output_paths
