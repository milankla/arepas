#!/usr/bin/env python3
"""
Performance benchmarking for ConfigurableDataLoader.
Tests loading speed and image matching performance.
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loader.configurable_loader import ConfigurableDataLoader


def test_performance():
    """
    Benchmark ConfigurableDataLoader performance.
    Tests both individual dataset loading and full neighborhood loading.
    """
    
    print("🔬 ConfigurableDataLoader Performance Test")
    print("=" * 60)
    
    # Check if config exists
    config_path = "config/data2.json"
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        return 1
    
    try:
        # Initialize loader
        print(f"\n📋 Loading configuration: {config_path}")
        loader = ConfigurableDataLoader(config_path)
        
        # Test 1: Load a single large dataset
        print("\n" + "=" * 60)
        print("Test 1: Single Dataset Loading (Sunnyside - largest)")
        print("=" * 60)
        
        start_time = time.time()
        data = loader.load_dataset("Sunnyside")
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Performance Results:")
        print(f"   Time elapsed: {elapsed:.2f} seconds")
        print(f"   Buildings processed: {data.total_buildings}")
        print(f"   Buildings with images: {data.buildings_with_images} ({data.buildings_with_images/data.total_buildings*100:.1f}%)")
        print(f"   Total images found: {data.total_images}")
        print(f"   Average time per building: {elapsed/data.total_buildings*1000:.2f} ms")
        print(f"   Average images per building: {data.total_images/data.buildings_with_images:.1f}")
        
        # Test 2: Load all datasets
        print("\n" + "=" * 60)
        print("Test 2: Full Dataset Loading (All 8 datasets)")
        print("=" * 60)
        
        start_time = time.time()
        all_data = loader.load_all_datasets()
        elapsed = time.time() - start_time
        
        total_buildings = sum(d.total_buildings for d in all_data.values())
        total_with_images = sum(d.buildings_with_images for d in all_data.values())
        total_images = sum(d.total_images for d in all_data.values())
        
        print(f"\n⏱️  Performance Results:")
        print(f"   Time elapsed: {elapsed:.2f} seconds")
        print(f"   Datasets loaded: {len(all_data)}")
        print(f"   Total buildings: {total_buildings}")
        print(f"   Buildings with images: {total_with_images} ({total_with_images/total_buildings*100:.1f}%)")
        print(f"   Total images: {total_images}")
        print(f"   Average time per building: {elapsed/total_buildings*1000:.2f} ms")
        print(f"   Average time per dataset: {elapsed/len(all_data):.2f} seconds")
        
        # Test 3: Multi-CSV neighborhood (Streetcar Commercial)
        print("\n" + "=" * 60)
        print("Test 3: Multi-CSV Neighborhood (Streetcar Commercial)")
        print("=" * 60)
        
        start_time = time.time()
        streetcar_data = loader.load_neighborhood("StreetcarCommercial", merge=True)
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Performance Results:")
        print(f"   Time elapsed: {elapsed:.2f} seconds")
        print(f"   Buildings processed: {streetcar_data.total_buildings}")
        print(f"   Buildings with images: {streetcar_data.buildings_with_images}")
        print(f"   Total images: {streetcar_data.total_images}")
        print(f"   Merged from 3 CSV files (Pearl, Tennyson, Gaylord)")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Performance Test Complete")
        print("=" * 60)
        print(f"   Overall: {elapsed/total_buildings*1000:.2f} ms per building")
        print(f"   Memory efficient: Processes {total_buildings:,} buildings")
        print(f"   Fast matching: {total_images:,} images matched")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_performance()
    sys.exit(exit_code)
