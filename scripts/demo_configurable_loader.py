#!/usr/bin/env python3
"""
Demo script showing ConfigurableDataLoader with summary reporting.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.loader.configurable_loader import ConfigurableDataLoader


def demo_data2_loading():
    """Demo loading data2 with summary reporting."""
    logger.info("=" * 60)
    logger.info("Demo: Loading data2/ with ConfigurableDataLoader")
    logger.info("=" * 60)
    
    # Load with config
    loader = ConfigurableDataLoader("config/data2.json")
    
    # Show config info
    info = loader.get_config_info()
    logger.info(f"\n📋 Configuration:")
    logger.info(f"  Description: {info['description']}")
    logger.info(f"  Structure type: {info['structure_type']}")
    logger.info(f"  Total datasets: {info['total_datasets']}")
    logger.info(f"  Neighborhoods: {', '.join(info['neighborhoods'])}")
    
    # Load all data
    logger.info(f"\n🔄 Loading all datasets...")
    all_data = loader.load_all_datasets()
    
    # Print summary
    loader.print_summary(all_data)
    
    # Get summary as dict
    summary = loader.get_summary(all_data)
    
    return all_data, summary


def demo_single_neighborhood():
    """Demo loading a single neighborhood with merging."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo: Loading Streetcar Commercial (3 sub-areas)")
    logger.info("=" * 60)
    
    loader = ConfigurableDataLoader("config/data2.json")
    
    # Load and merge Streetcar Commercial
    logger.info("\n🔄 Loading Streetcar Commercial with merge=True...")
    data = loader.load_neighborhood("StreetcarCommercial", merge=True)
    
    logger.info(f"\n✅ Merged Result:")
    logger.info(f"  Name: {data.name}")
    logger.info(f"  Total buildings: {data.total_buildings}")
    logger.info(f"  Buildings with images: {data.buildings_with_images}")
    logger.info(f"  Total images: {data.total_images}")
    
    return data


def demo_comparison():
    """Compare data/ vs data2/ structures."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo: Comparing data/ vs data2/ structures")
    logger.info("=" * 60)
    
    # Load data2
    loader_data2 = ConfigurableDataLoader("config/data2.json")
    data2 = loader_data2.load_all_datasets()
    summary_data2 = loader_data2.get_summary(data2)
    
    logger.info(f"\n📊 data2/ structure (neighborhood-based):")
    logger.info(f"  Datasets: {summary_data2['total_datasets']}")
    logger.info(f"  Buildings: {summary_data2['total_buildings']}")
    logger.info(f"  Images: {summary_data2['total_images']}")
    
    # Could load data/ too if config/data.json is ready
    # loader_data = ConfigurableDataLoader("config/data.json")
    # data = loader_data.load_all_datasets()
    # summary_data = loader_data.get_summary(data)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # Run demos
    try:
        # Demo 1: Load all data with summary
        all_data, summary = demo_data2_loading()
        
        # Demo 2: Load single neighborhood
        streetcar_data = demo_single_neighborhood()
        
        # Demo 3: Comparison (if data/ config exists)
        # demo_comparison()
        
        logger.success("\n🎉 All demos completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
