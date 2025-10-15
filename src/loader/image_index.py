"""
Image indexing and pattern matching utilities.
"""

import os
from typing import Dict, List, Set
from loguru import logger


class ImageIndex:
    """
    Manages image file indexing and pattern matching for fast lookups.
    """
    
    def __init__(self, images_dir: str, image_extensions: set = None):
        self.images_dir = images_dir
        # Configurable image extensions
        self.IMAGE_EXTENSIONS = image_extensions or {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        self._index: Dict[str, List[str]] = {}
        self._built = False
    
    def find_images(self, building_id: str, smithsonian: str = None) -> List[str]:
        """
        Find images for a building using ID and optional smithsonian number.
        
        Args:
            building_id: Primary building identifier
            smithsonian: Optional smithsonian number
            
        Returns:
            List of image file paths
        """
        if not self._built:
            self._build_index()
        
        patterns = self._generate_patterns(building_id, smithsonian)
        return self._search_by_patterns(patterns)
    
    def _build_index(self) -> None:
        """Build the image index for fast lookups."""
        if self._built:
            return
        
        logger.debug(f"Building image index for: {self.images_dir}")
        
        try:
            all_files = os.listdir(self.images_dir)
            image_files = [f for f in all_files if self._is_image_file(f)]
            
            logger.info(f"Found {len(image_files)} images in {os.path.basename(self.images_dir)}")
            
            for filename in image_files:
                self._index_file(filename)
                
            self._built = True
            logger.info(f"Built index with {len(self._index)} entries")
            
        except Exception as e:
            logger.error(f"Error building image index: {e}")
            self._index = {}
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension."""
        return any(filename.endswith(ext) for ext in self.IMAGE_EXTENSIONS)
    
    def _index_file(self, filename: str) -> None:
        """Index a single image file with multiple lookup keys."""
        name_without_ext = os.path.splitext(filename)[0]
        full_path = os.path.join(self.images_dir, filename)
        
        # Index by full filename (without extension)
        self._add_to_index(name_without_ext, full_path)
        
        # Index by underscore-separated parts
        self._index_by_underscore_parts(name_without_ext, full_path)
        
        # Index by dot-separated parts (for smithsonian numbers)
        self._index_by_dot_parts(name_without_ext, full_path)
    
    def _add_to_index(self, key: str, path: str) -> None:
        """Add a path to the index under a specific key."""
        if key not in self._index:
            self._index[key] = []
        if path not in self._index[key]:
            self._index[key].append(path)
    
    def _index_by_underscore_parts(self, name: str, full_path: str) -> None:
        """Index by underscore-separated parts."""
        parts = name.split('_')
        if len(parts) > 1:
            # Index by first part (e.g., "5DV.1011" from "5DV.1011_3280_N_DOWNING_ST")
            self._add_to_index(parts[0], full_path)
    
    def _index_by_dot_parts(self, name: str, full_path: str) -> None:
        """Index by dot-separated parts for smithsonian numbers."""
        dot_parts = name.split('.')
        if len(dot_parts) > 1:
            # Index by progressive combinations (5DV, 5DV.1011, 5DV.1011.xyz)
            for i in range(1, len(dot_parts) + 1):
                prefix = '.'.join(dot_parts[:i])
                self._add_to_index(prefix, full_path)
    
    def _generate_patterns(self, building_id: str, smithsonian: str = None) -> List[str]:
        """Generate search patterns ordered by likelihood of success."""
        patterns = []
        
        # Try smithsonian patterns first (most specific)
        if smithsonian and smithsonian not in ('nan', 'null', ''):
            patterns.extend([
                smithsonian,           # Direct match
                f"{smithsonian}_",     # With underscore prefix
            ])
        
        # Try building ID patterns
        patterns.append(building_id)
        
        # Additional patterns for 5DV format
        if building_id.startswith('5DV.'):
            patterns.extend([
                f"{building_id}_",
            ])
        
        return patterns
    
    def _search_by_patterns(self, patterns: List[str]) -> List[str]:
        """Search index using patterns."""
        found_images = []
        
        for pattern in patterns:
            # Direct lookup
            if pattern in self._index:
                found_images.extend(self._index[pattern])
                continue
            
            # Prefix matching
            matches = [
                img for key in self._index
                if key.startswith(pattern)
                for img in self._index[key]
            ]
            found_images.extend(matches)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(found_images))
