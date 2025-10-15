"""
Configuration classes for data loading.

This module defines the JSON configuration structure for mapping datasets
to their CSV and image locations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class DatasetConfig:
    """Configuration for a single dataset."""
    name: str
    csv_file: str
    images_dir: str
    metadata: Optional[Dict[str, str]] = None
    
    @property
    def neighborhood(self) -> Optional[str]:
        """Get neighborhood from metadata."""
        return self.metadata.get('neighborhood') if self.metadata else None
    
    @property
    def style(self) -> Optional[str]:
        """Get style from metadata."""
        return self.metadata.get('style') if self.metadata else None
    
    def validate(self, base_path: Path) -> bool:
        """Validate that configured paths exist."""
        csv_path = base_path / self.csv_file
        img_path = base_path / self.images_dir
        
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return False
        if not img_path.exists():
            logger.error(f"Images directory not found: {img_path}")
            return False
        
        return True


@dataclass  
class DataStructureConfig:
    """Top-level configuration for data structure."""
    version: str
    description: str
    structure_type: str
    base_path: str
    datasets: List[DatasetConfig]
    notes: Optional[List[str]] = None
    
    @classmethod
    def from_json(cls, json_path: str) -> 'DataStructureConfig':
        """Load configuration from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        datasets = [
            DatasetConfig(
                name=ds['name'],
                csv_file=ds['csv_file'],
                images_dir=ds['images_dir'],
                metadata=ds.get('metadata')
            )
            for ds in data.get('datasets', [])
        ]
        
        return cls(
            version=data.get('version', '1.0'),
            description=data.get('description', ''),
            structure_type=data.get('structure_type', 'unknown'),
            base_path=data.get('base_path', '.'),
            datasets=datasets,
            notes=data.get('notes')
        )
    
    def get_dataset(self, name: str) -> Optional[DatasetConfig]:
        """Get dataset configuration by name."""
        for ds in self.datasets:
            if ds.name == name:
                return ds
        return None
    
    def get_datasets_by_neighborhood(self, neighborhood: str) -> List[DatasetConfig]:
        """Get all datasets for a specific neighborhood."""
        return [
            ds for ds in self.datasets 
            if ds.neighborhood == neighborhood
        ]
    
    def list_neighborhoods(self) -> List[str]:
        """Get list of unique neighborhoods in config."""
        neighborhoods = set()
        for ds in self.datasets:
            if ds.neighborhood:
                neighborhoods.add(ds.neighborhood)
        return sorted(list(neighborhoods))
