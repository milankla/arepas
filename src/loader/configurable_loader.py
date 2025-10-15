"""
Configuration-driven data loader for Arepas project.

This module provides a flexible data loading system that uses JSON configuration files
to map datasets to their CSV and image locations, supporting any directory structure.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
from loguru import logger

try:
    from .csv_parser import RobustCSVParser
    from .image_index import ImageIndex
    from .load_config import DataStructureConfig
except ImportError:
    from csv_parser import RobustCSVParser
    from image_index import ImageIndex
    from load_config import DataStructureConfig


@dataclass
class NeighborhoodData:
    """Container for neighborhood loading results."""
    name: str
    buildings: Dict[str, Dict[str, Any]]
    total_buildings: int
    buildings_with_images: int
    total_images: int


class ConfigurableDataLoader:
    """
    Data loader that uses JSON configuration files to locate CSVs and images.
    
    This loader supports any directory structure by reading explicit mappings
    from a configuration file. No structure detection needed.
    """
    
    def __init__(self, config_path: str = "config/data2.json"):
        """
        Initialize loader with configuration file.
        
        Args:
            config_path: Path to JSON configuration file
        """
        self.config_path = Path(config_path)
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        logger.info(f"Loading configuration from: {config_path}")
        self.config = DataStructureConfig.from_json(str(self.config_path))
        self.base_path = Path(self.config.base_path)
        
        self.csv_parser = RobustCSVParser()
        
        # Validate all datasets
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all configured paths exist."""
        invalid = []
        for dataset in self.config.datasets:
            if not dataset.validate(self.base_path):
                invalid.append(dataset.name)
        
        if invalid:
            logger.warning(f"Invalid datasets in config: {invalid}")
        else:
            logger.info(f"Configuration valid: {len(self.config.datasets)} datasets")
    
    def load_dataset(self, dataset_name: str) -> NeighborhoodData:
        """
        Load a specific dataset by name.
        
        Args:
            dataset_name: Name of dataset as defined in config
            
        Returns:
            NeighborhoodData object with loaded buildings
        """
        dataset_config = self.config.get_dataset(dataset_name)
        
        if not dataset_config:
            raise ValueError(f"Dataset '{dataset_name}' not found in configuration")
        
        logger.info(f"Loading dataset: {dataset_name}")
        
        # Build full paths
        csv_path = self.base_path / dataset_config.csv_file
        images_dir = self.base_path / dataset_config.images_dir
        
        # Load CSV
        logger.debug(f"Loading CSV: {csv_path}")
        df = self.csv_parser.parse_file(str(csv_path))
        logger.info(f"Loaded {len(df)} records from CSV")
        
        # Create image index
        logger.debug(f"Building image index: {images_dir}")
        image_index = ImageIndex(str(images_dir))
        
        # Build building data
        buildings = self._build_building_data(df, image_index, dataset_name)
        
        # Calculate statistics
        buildings_with_images = sum(1 for info in buildings.values() if info['images'])
        total_images = sum(len(info['images']) for info in buildings.values())
        
        logger.info(f"Dataset {dataset_name}: {len(buildings)} buildings, "
                   f"{buildings_with_images} with images, {total_images} total images")
        
        return NeighborhoodData(
            name=dataset_name,
            buildings=buildings,
            total_buildings=len(buildings),
            buildings_with_images=buildings_with_images,
            total_images=total_images
        )
    
    def load_all_datasets(self) -> Dict[str, NeighborhoodData]:
        """
        Load all datasets defined in configuration.
        
        Returns:
            Dictionary mapping dataset names to NeighborhoodData
        """
        results = {}
        
        for dataset_config in self.config.datasets:
            try:
                result = self.load_dataset(dataset_config.name)
                results[dataset_config.name] = result
            except Exception as e:
                logger.error(f"Failed to load dataset {dataset_config.name}: {e}")
                continue
        
        return results
    
    def load_neighborhood(self, neighborhood: str, merge: bool = True) -> NeighborhoodData:
        """
        Load all datasets for a specific neighborhood.
        
        Args:
            neighborhood: Neighborhood name
            merge: If True, merge multiple style datasets into one
            
        Returns:
            NeighborhoodData (merged if multiple datasets exist)
        """
        dataset_configs = self.config.get_datasets_by_neighborhood(neighborhood)
        
        if not dataset_configs:
            raise ValueError(f"No datasets found for neighborhood '{neighborhood}'")
        
        logger.info(f"Loading {len(dataset_configs)} dataset(s) for {neighborhood}")
        
        # Load all datasets for this neighborhood
        datasets = []
        for config in dataset_configs:
            try:
                data = self.load_dataset(config.name)
                datasets.append(data)
            except Exception as e:
                logger.error(f"Failed to load {config.name}: {e}")
                continue
        
        if not datasets:
            raise RuntimeError(f"Failed to load any datasets for {neighborhood}")
        
        # If only one dataset or no merge requested, return as-is
        if len(datasets) == 1 or not merge:
            return datasets[0]
        
        # Merge multiple datasets
        logger.info(f"Merging {len(datasets)} datasets for {neighborhood}")
        return self._merge_datasets(datasets, neighborhood)
    
    def _merge_datasets(self, datasets: List[NeighborhoodData], 
                       neighborhood: str) -> NeighborhoodData:
        """Merge multiple NeighborhoodData objects into one."""
        merged_buildings = {}
        
        for dataset in datasets:
            for building_id, building_info in dataset.buildings.items():
                if building_id in merged_buildings:
                    # Conflict: same building ID in multiple datasets
                    logger.warning(f"Duplicate building ID {building_id} in {dataset.name}")
                    # Create unique key
                    unique_key = f"{building_id}_{dataset.name}"
                    merged_buildings[unique_key] = building_info
                else:
                    merged_buildings[building_id] = building_info
        
        # Calculate merged statistics
        buildings_with_images = sum(1 for info in merged_buildings.values() if info['images'])
        total_images = sum(len(info['images']) for info in merged_buildings.values())
        
        logger.info(f"Merged {neighborhood}: {len(merged_buildings)} buildings, "
                   f"{buildings_with_images} with images")
        
        return NeighborhoodData(
            name=neighborhood,
            buildings=merged_buildings,
            total_buildings=len(merged_buildings),
            buildings_with_images=buildings_with_images,
            total_images=total_images
        )
    
    def _build_building_data(self, df: pd.DataFrame, image_index: ImageIndex,
                            dataset_name: str) -> Dict[str, Dict[str, Any]]:
        """Build building data dictionary from DataFrame."""
        buildings = {}
        
        # Find ID column
        id_column = self._find_id_column(df)
        if not id_column:
            logger.error(f"No ID column found in {dataset_name}. Columns: {list(df.columns)}")
            return {}
        
        logger.debug(f"Using ID column: {id_column}")
        
        for idx, row in df.iterrows():
            try:
                building_id = str(row[id_column])
                smithsonian = str(row.get('smithsonianNumber', '')).strip()
                
                # Find images for this building
                images = image_index.find_images(building_id, smithsonian)
                
                buildings[building_id] = {
                    'attributes': row,
                    'images': images,
                    'dataset': dataset_name
                }
                
            except Exception as e:
                logger.warning(f"Skipping row {idx} in {dataset_name}: {e}")
                continue
        
        return buildings
    
    def _find_id_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the appropriate ID column in DataFrame."""
        # Try exact match first
        if 'id' in df.columns:
            return 'id'
        
        # Look for columns containing 'id' (case-insensitive)
        id_columns = [col for col in df.columns if 'id' in col.lower()]
        if id_columns:
            logger.debug(f"Found ID columns: {id_columns}, using {id_columns[0]}")
            return id_columns[0]
        
        return None
    
    def list_datasets(self) -> List[str]:
        """Get list of all dataset names in configuration."""
        return [ds.name for ds in self.config.datasets]
    
    def list_neighborhoods(self) -> List[str]:
        """Get list of all unique neighborhoods in configuration."""
        return self.config.list_neighborhoods()
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get summary information about the configuration."""
        return {
            'config_path': str(self.config_path),
            'version': self.config.version,
            'description': self.config.description,
            'structure_type': self.config.structure_type,
            'total_datasets': len(self.config.datasets),
            'neighborhoods': self.list_neighborhoods(),
            'datasets': self.list_datasets()
        }
    
    def get_summary(self, data: Dict[str, NeighborhoodData]) -> Dict[str, Any]:
        """
        Generate summary statistics for loaded data.
        
        Args:
            data: Dictionary of loaded NeighborhoodData objects
            
        Returns:
            Dictionary with summary statistics
        """
        total_buildings = sum(d.total_buildings for d in data.values())
        total_buildings_with_images = sum(d.buildings_with_images for d in data.values())
        total_images = sum(d.total_images for d in data.values())
        
        return {
            'total_datasets': len(data),
            'total_buildings': total_buildings,
            'total_buildings_with_images': total_buildings_with_images,
            'total_images': total_images,
            'coverage_percentage': (total_buildings_with_images / total_buildings * 100) if total_buildings > 0 else 0.0,
            'average_images_per_building': (total_images / total_buildings) if total_buildings > 0 else 0.0,
            'datasets': {
                name: {
                    'buildings': d.total_buildings,
                    'buildings_with_images': d.buildings_with_images,
                    'total_images': d.total_images,
                    'coverage': (d.buildings_with_images / d.total_buildings * 100) if d.total_buildings > 0 else 0.0
                }
                for name, d in data.items()
            }
        }
    
    def print_summary(self, data: Dict[str, NeighborhoodData]) -> None:
        """
        Print a formatted summary of loaded data.
        
        Args:
            data: Dictionary of loaded NeighborhoodData objects
        """
        logger.info("\n" + "=" * 60)
        logger.info("DATA LOADING SUMMARY")
        logger.info("=" * 60)
        
        # Per-dataset statistics
        for name, dataset in data.items():
            coverage = (dataset.buildings_with_images / dataset.total_buildings * 100) if dataset.total_buildings > 0 else 0.0
            logger.info(f"\n📊 {name}:")
            logger.info(f"  Buildings: {dataset.total_buildings}")
            logger.info(f"  Buildings with images: {dataset.buildings_with_images} ({coverage:.1f}%)")
            logger.info(f"  Total images: {dataset.total_images}")
        
        # Overall statistics
        summary = self.get_summary(data)
        logger.info("\n" + "=" * 60)
        logger.success(f"✅ TOTAL: {summary['total_datasets']} datasets")
        logger.success(f"   Buildings: {summary['total_buildings']}")
        logger.success(f"   With images: {summary['total_buildings_with_images']} ({summary['coverage_percentage']:.1f}%)")
        logger.success(f"   Total images: {summary['total_images']}")
        logger.success(f"   Avg images/building: {summary['average_images_per_building']:.1f}")
        logger.info("=" * 60 + "\n")


# Convenience function for quick loading
def load_from_config(config_path: str = "config/data2.json") -> ConfigurableDataLoader:
    """
    Create a ConfigurableDataLoader from a config file.
    
    Args:
        config_path: Path to JSON configuration file
        
    Returns:
        ConfigurableDataLoader instance
    """
    return ConfigurableDataLoader(config_path)


# Main execution when run as script
if __name__ == "__main__":
    import sys
    
    # Configure logging for direct execution
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # Determine which config to use
    config_path = "config/data2.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    logger.info(f"Starting ConfigurableDataLoader with config: {config_path}")
    
    try:
        # Initialize loader
        loader = ConfigurableDataLoader(config_path)
        
        # Show configuration info
        info = loader.get_config_info()
        logger.info(f"\n📋 Configuration Info:")
        logger.info(f"  Description: {info['description']}")
        logger.info(f"  Structure type: {info['structure_type']}")
        logger.info(f"  Total datasets: {info['total_datasets']}")
        logger.info(f"  Neighborhoods: {', '.join(info['neighborhoods'])}")
        
        # Load all datasets
        logger.info(f"\n🔄 Loading all datasets...")
        all_data = loader.load_all_datasets()
        
        # Print summary
        loader.print_summary(all_data)
        
        logger.success("✅ Data loading completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
