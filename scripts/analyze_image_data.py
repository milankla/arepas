"""
Analyze Image Dataset for Multi-Task Learning

Uses existing ConfigurableDataLoader to:
1. Load building records from /data/*.txt files
2. Match images to records via smithsonianNumber
3. Analyze class distribution for all 25 target fields
4. Report data readiness for training

This script leverages our production-ready data loading infrastructure.
"""

import sys
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import json
from PIL import Image
import numpy as np
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loader.configurable_loader import ConfigurableDataLoader
from src.log_config import setup_logging


# Target fields for multi-task learning (25 total)
TARGET_FIELDS = {
    # Phase 1 Track 2: Easy visual features (Tier 1)
    'phase1': [
        'Stories',
        'Roof Type', 
        'Primary Cladding',
        'Setting',
        'Chimney',
        'Window',
        'Entrance',
    ],
    
    # Phase 2: Add Tier 2 architectural classification
    'phase2': [
        'Stories',
        'Roof Type', 
        'Primary Cladding',
        'Setting',
        'Chimney',
        'Window',
        'Entrance',
        'Architectural Style',
        'Building Form',
        'Roof Features',
        'Wall Features',
    ],
    
    # Legacy groupings for comprehensive analysis
    'easy': [
        'Stories',
        'Roof Type', 
        'Primary Cladding',
        'Setting',
        'Chimney',
        'Window',
        'Entrance',
    ],
    
    # Architectural classification (Phase 2)
    'medium': [
        'Architectural Style',
        'Building Form',
        'Building Category',
        'Current Use',
        'Original Use',
    ],
    
    # Fine-grained features (Phase 3)
    'hard': [
        'Building Plan',
        'Roof Features',
        'Additional Cladding',
        'Roof Materials',
        'Wall Features',
        'Landscape Features',
        'Associated Building and Objects',
    ],
    
    # Alteration detection (Phase 4)
    'very_hard': [
        'Alteration Level',
        'Alterations-Additions',
        'Alterations-Entrances',
        'Alterations-Roof',
        'Alterations-Cladding',
        'Alterations-Windows',
    ]
}


def find_image_folders(data_dir: Path) -> dict:
    """
    Find all image folders in data directory
    
    Expected structure:
        /data/Bungalows/Bungalows - Photos/*.jpg
        /data/Minimal Traditional/Minimal Traditional - Photos/*.jpg
    
    Returns:
        Dict mapping style name to image folder path
    """
    image_folders = {}
    
    for style_dir in data_dir.iterdir():
        if not style_dir.is_dir() or style_dir.name.startswith('.'):
            continue
        
        # Look for "X - Photos" folder
        photo_folder = style_dir / f"{style_dir.name} - Photos"
        if photo_folder.exists():
            image_folders[style_dir.name] = photo_folder
            logger.info(f"Found image folder: {photo_folder}")
    
    return image_folders


def count_images_by_survey_id(image_folder: Path) -> dict:
    """
    Count images grouped by survey ID
    
    Image naming: {surveyID}_{address}.{hash}.jpg
    Example: 5DV.4594_3226_N_RACE_ST.abc123.jpg
    
    Returns:
        Dict mapping survey_id to list of image paths
    """
    images_by_id = defaultdict(list)
    
    for img_path in image_folder.glob("*.jpg"):
        # Extract survey ID from filename
        filename = img_path.stem  # Remove .jpg
        
        # Survey ID is everything before first underscore
        if '_' in filename:
            survey_id = filename.split('_')[0]
            images_by_id[survey_id].append(img_path)
    
    return dict(images_by_id)


def analyze_image_quality(image_paths: list, sample_size: int = 100) -> dict:
    """
    Analyze image quality metrics for preprocessing decisions
    
    Args:
        image_paths: List of image file paths
        sample_size: Number of images to sample for quality checks
        
    Returns:
        Dict with quality statistics
    """
    if not image_paths:
        return {}
    
    # Sample images for quality analysis
    sample_paths = np.random.choice(image_paths, min(sample_size, len(image_paths)), replace=False)
    
    sizes = []
    aspect_ratios = []
    corrupted = []
    file_sizes = []
    
    for img_path in sample_paths:
        try:
            # Check file size
            file_size_kb = img_path.stat().st_size / 1024
            file_sizes.append(file_size_kb)
            
            # Open and analyze image
            with Image.open(img_path) as img:
                width, height = img.size
                sizes.append((width, height))
                aspect_ratios.append(width / height)
                
        except Exception as e:
            corrupted.append((str(img_path), str(e)))
            logger.warning(f"Corrupted/unreadable image: {img_path}")
    
    if not sizes:
        return {'error': 'No valid images found'}
    
    widths = [s[0] for s in sizes]
    heights = [s[1] for s in sizes]
    
    return {
        'total_sampled': len(sample_paths),
        'corrupted_count': len(corrupted),
        'corrupted_files': corrupted[:10],  # First 10 corrupted files
        'width': {
            'min': min(widths),
            'max': max(widths),
            'mean': np.mean(widths),
            'median': np.median(widths),
            'std': np.std(widths)
        },
        'height': {
            'min': min(heights),
            'max': max(heights),
            'mean': np.mean(heights),
            'median': np.median(heights),
            'std': np.std(heights)
        },
        'aspect_ratio': {
            'min': min(aspect_ratios),
            'max': max(aspect_ratios),
            'mean': np.mean(aspect_ratios),
            'median': np.median(aspect_ratios),
            'std': np.std(aspect_ratios)
        },
        'file_size_kb': {
            'min': min(file_sizes),
            'max': max(file_sizes),
            'mean': np.mean(file_sizes),
            'median': np.median(file_sizes)
        }
    }


def analyze_field_distribution(buildings: list, field_name: str) -> dict:
    """
    Analyze value distribution for a specific field
    
    Args:
        buildings: List of building dictionaries
        field_name: Name of field to analyze
        
    Returns:
        Dict with statistics
    """
    values = []
    missing = 0
    
    for building in buildings:
        value = building.get(field_name, '')
        
        if not value or value == 'null' or str(value).strip() == '':
            missing += 1
        else:
            values.append(str(value).strip())
    
    value_counts = Counter(values)
    
    return {
        'field_name': field_name,
        'total_records': len(buildings),
        'missing': missing,
        'missing_pct': (missing / len(buildings) * 100) if buildings else 0,
        'unique_values': len(value_counts),
        'top_values': value_counts.most_common(10),
        'value_counts': dict(value_counts)
    }


def analyze_dataset(data_dir: Path = Path('./data'), phase: str = 'all', output_json: Path = None):
    """
    Comprehensive analysis of image dataset using existing data loader
    
    Args:
        data_dir: Path to data directory
        phase: Which phase to analyze ('phase1', 'phase2', or 'all')
        output_json: Path to save JSON report (optional)
    """
    logger.info("="*80)
    logger.info(f"ANALYZING IMAGE DATASET - {phase.upper()}")
    logger.info("="*80)
    
    # Determine which fields to analyze based on phase
    if phase in ['phase1', 'phase2']:
        active_fields = TARGET_FIELDS[phase]
        logger.info(f"Analyzing {len(active_fields)} fields for {phase.upper()}")
    else:
        active_fields = []
        for difficulty, fields in TARGET_FIELDS.items():
            if difficulty not in ['phase1', 'phase2']:  # Skip phase-specific keys
                active_fields.extend(fields)
        logger.info(f"Analyzing all {len(active_fields)} fields")
    
    # Find image folders
    image_folders = find_image_folders(data_dir)
    
    if not image_folders:
        logger.warning(f"No image folders found in {data_dir}")
        logger.info("Expected structure: {data_dir}/Style Name/Style Name - Photos/*.jpg")
        return
    
    logger.info(f"\nFound {len(image_folders)} architectural styles with images:")
    for style, folder in image_folders.items():
        num_images = len(list(folder.glob("*.jpg")))
        logger.info(f"  - {style}: {num_images} images")
    
    # Load ALL datasets using ConfigurableDataLoader
    logger.info("\n" + "="*80)
    logger.info("LOADING BUILDING RECORDS")
    logger.info("="*80)
    
    config_path = data_dir.parent / 'config' / 'data.json'
    # Support data2/ with its own config
    if 'data2' in str(data_dir):
        config_path = data_dir.parent / 'config' / 'data2.json'
    
    loader = ConfigurableDataLoader(config_path=str(config_path))
    all_datasets = loader.load_all_datasets()
    
    all_buildings = []
    buildings_by_style = {}
    
    for dataset_name, neighborhood_data in all_datasets.items():
        # Get style from config metadata
        dataset_config = loader.config.get_dataset(dataset_name)
        style = dataset_config.metadata.get('style', dataset_name) if dataset_config.metadata else dataset_name
        
        logger.info(f"  {dataset_name}: {neighborhood_data.total_buildings} buildings")
        
        # NeighborhoodData.buildings: {id -> {attributes: {col: {value:...}}, images: [...]}}
        flat_buildings = []
        for building_id, building_data in neighborhood_data.buildings.items():
            # Flatten attributes: {col: {value: v}} -> {col: v}
            flat = {col: entry['value'] 
                    for col, entry in building_data.get('attributes', {}).items()}
            flat['_building_id'] = building_id
            flat['_dataset_name'] = dataset_name
            flat['_dataset_style'] = style
            flat['_image_paths'] = [Path(p) for p in building_data.get('images', [])]
            flat['_num_images'] = len(flat['_image_paths'])
            flat_buildings.append(flat)
        
        all_buildings.extend(flat_buildings)
        
        if style not in buildings_by_style:
            buildings_by_style[style] = []
        buildings_by_style[style].extend(flat_buildings)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"TOTAL BUILDINGS LOADED: {len(all_buildings)}")
    logger.info(f"{'='*80}")
    
    # Match images to buildings using data already indexed by ConfigurableDataLoader
    logger.info("\n" + "="*80)
    logger.info("MATCHING IMAGES TO BUILDING RECORDS")
    logger.info("="*80)
    
    matched_count = 0
    unmatched_buildings = 0
    
    buildings_with_images = []
    
    for dataset_name, neighborhood_data in all_datasets.items():
        with_imgs = neighborhood_data.buildings_with_images
        total = neighborhood_data.total_buildings
        logger.info(f"  {dataset_name}: {with_imgs}/{total} buildings have images")
    
    # Split flat buildings into matched/unmatched
    for building in all_buildings:
        if building.get('_num_images', 0) > 0:
            buildings_with_images.append(building)
            matched_count += 1
        else:
            unmatched_buildings += 1
    
    # Count image IDs in folders that don't appear in any building record
    all_image_ids_in_folders = set()
    all_matched_ids = set()
    for style, folder in image_folders.items():
        for sid in count_images_by_survey_id(folder):
            all_image_ids_in_folders.add(sid)
    for b in buildings_with_images:
        sid = str(b.get('smithsonianNumber', '')).strip()
        if sid:
            all_matched_ids.add(sid)
    unmatched_images = len(all_image_ids_in_folders - all_matched_ids)
    
    logger.info(f"\n{'='*80}")
    logger.info("MATCHING SUMMARY:")
    logger.info(f"  ✓ Buildings with images: {matched_count}")
    logger.info(f"  ⚠ Buildings without images: {unmatched_buildings}")
    logger.info(f"  ⚠ Images without building records: {unmatched_images}")
    logger.info(f"{'='*80}")
    
    # Image quality analysis (for preprocessing decisions)
    logger.info("\n" + "="*80)
    logger.info("IMAGE QUALITY ANALYSIS (for preprocessing)")
    logger.info("="*80)
    
    all_image_paths = []
    for building in buildings_with_images:
        all_image_paths.extend(building['_image_paths'])
    
    if all_image_paths:
        logger.info(f"\nAnalyzing sample of {min(100, len(all_image_paths))} images...")
        quality_stats = analyze_image_quality(all_image_paths, sample_size=100)
        
        if 'error' not in quality_stats:
            logger.info(f"\nImage Dimensions:")
            logger.info(f"  Width:  {quality_stats['width']['min']:.0f} - {quality_stats['width']['max']:.0f} px (mean: {quality_stats['width']['mean']:.0f})")
            logger.info(f"  Height: {quality_stats['height']['min']:.0f} - {quality_stats['height']['max']:.0f} px (mean: {quality_stats['height']['mean']:.0f})")
            logger.info(f"  Aspect Ratio: {quality_stats['aspect_ratio']['min']:.2f} - {quality_stats['aspect_ratio']['max']:.2f} (mean: {quality_stats['aspect_ratio']['mean']:.2f})")
            
            logger.info(f"\nFile Sizes:")
            logger.info(f"  Range: {quality_stats['file_size_kb']['min']:.0f} - {quality_stats['file_size_kb']['max']:.0f} KB")
            logger.info(f"  Mean: {quality_stats['file_size_kb']['mean']:.0f} KB")
            
            if quality_stats['corrupted_count'] > 0:
                logger.warning(f"\n⚠ Found {quality_stats['corrupted_count']} corrupted/unreadable images")
                for img_path, error in quality_stats['corrupted_files'][:5]:
                    logger.warning(f"  - {img_path}: {error}")
            else:
                logger.info(f"\n✓ No corrupted images detected")
            
            # Preprocessing recommendations
            logger.info(f"\nPreprocessing Recommendations:")
            mean_width = quality_stats['width']['mean']
            mean_height = quality_stats['height']['mean']
            mean_aspect = quality_stats['aspect_ratio']['mean']
            
            if mean_width < 512 or mean_height < 512:
                logger.warning(f"  ⚠ Images are small (avg {mean_width:.0f}x{mean_height:.0f}). Recommend 512x512 or higher.")
            else:
                logger.info(f"  ✓ Image resolution sufficient for deep learning (avg {mean_width:.0f}x{mean_height:.0f})")
            
            if quality_stats['aspect_ratio']['std'] > 0.3:
                logger.info(f"  → High aspect ratio variance. Crop preprocessing recommended.")
            else:
                logger.info(f"  → Consistent aspect ratios. Center crop may suffice.")
    
    # Analyze field distributions for multi-task learning
    logger.info("\n" + "="*80)
    logger.info(f"FIELD DISTRIBUTION ANALYSIS ({len(active_fields)} Target Fields)")
    logger.info("="*80)
    
    field_stats = {}
    
    for field in active_fields:
        stats = analyze_field_distribution(buildings_with_images, field)
        field_stats[field] = stats
        
        logger.info(f"\n{field}:")
        logger.info(f"  Total records: {stats['total_records']}")
        logger.info(f"  Missing: {stats['missing']} ({stats['missing_pct']:.1f}%)")
        logger.info(f"  Unique values: {stats['unique_values']}")
        
        if stats['unique_values'] > 0:
            logger.info(f"  Top values:")
            for value, count in stats['top_values'][:5]:
                pct = count / stats['total_records'] * 100
                logger.info(f"    - {value}: {count} ({pct:.1f}%)")
    
    # Image distribution analysis
    logger.info("\n" + "="*80)
    logger.info("IMAGE DISTRIBUTION")
    logger.info("="*80)
    
    images_per_building = [b['_num_images'] for b in buildings_with_images]
    
    if images_per_building:
        logger.info(f"  Total buildings with images: {len(buildings_with_images)}")
        logger.info(f"  Total images: {sum(images_per_building)}")
        logger.info(f"  Images per building:")
        logger.info(f"    - Min: {min(images_per_building)}")
        logger.info(f"    - Max: {max(images_per_building)}")
        logger.info(f"    - Average: {sum(images_per_building) / len(images_per_building):.1f}")
        logger.info(f"    - Median: {sorted(images_per_building)[len(images_per_building)//2]}")
    
    # Training readiness assessment
    logger.info("\n" + "="*80)
    logger.info("TRAINING READINESS ASSESSMENT")
    logger.info("="*80)
    
    ready_fields = []
    warning_fields = []
    not_ready_fields = []
    
    for field, stats in field_stats.items():
        missing_pct = stats['missing_pct']
        unique_values = stats['unique_values']
        
        # Assess readiness
        if missing_pct < 10 and unique_values >= 2:
            ready_fields.append(field)
        elif missing_pct < 30 and unique_values >= 2:
            warning_fields.append(field)
        else:
            not_ready_fields.append(field)
    
    logger.info(f"\n✓ READY FOR TRAINING ({len(ready_fields)} fields):")
    for field in ready_fields:
        stats = field_stats[field]
        logger.info(f"  - {field}: {stats['unique_values']} classes, {stats['missing_pct']:.1f}% missing")
    
    if warning_fields:
        logger.info(f"\n⚠ WARNING - HIGH MISSING DATA ({len(warning_fields)} fields):")
        for field in warning_fields:
            stats = field_stats[field]
            logger.info(f"  - {field}: {stats['unique_values']} classes, {stats['missing_pct']:.1f}% missing")
    
    if not_ready_fields:
        logger.info(f"\n✗ NOT READY - INSUFFICIENT DATA ({len(not_ready_fields)} fields):")
        for field in not_ready_fields:
            stats = field_stats[field]
            logger.info(f"  - {field}: {stats['unique_values']} classes, {stats['missing_pct']:.1f}% missing")
    
    # Recommendations
    logger.info("\n" + "="*80)
    logger.info(f"RECOMMENDATIONS - {phase.upper()}")
    logger.info("="*80)
    
    if phase == 'phase1':
        logger.info(f"\nPHASE 1 TRACK 2: TIER 1 TASKS ({len([f for f in active_fields if f in ready_fields])} ready):")
        for field in active_fields:
            if field in ready_fields:
                logger.info(f"   ✓ {field}")
            elif field in warning_fields:
                logger.info(f"   ⚠ {field} (high missing data)")
            else:
                logger.info(f"   ✗ {field} (not ready)")
        
        logger.info(f"\nPHASE 1 TRACK 1: IMAGE PREPROCESSING")
        logger.info(f"   → Run YOLOv8 building detection on all images")
        logger.info(f"   → Generate cropped 512x512 images")
        logger.info(f"   → Save to {data_dir}/preprocessed/")
        logger.info(f"   → Quality control: Review 100 random crops")
    
    elif phase == 'phase2':
        tier1_ready = len([f for f in TARGET_FIELDS['phase1'] if f in ready_fields])
        tier2_ready = len([f for f in active_fields if f not in TARGET_FIELDS['phase1'] and f in ready_fields])
        
        logger.info(f"\nPHASE 2: TIER 1 + TIER 2 TASKS")
        logger.info(f"   - Tier 1 (carry over): {tier1_ready}/7 ready")
        logger.info(f"   - Tier 2 (new): {tier2_ready}/4 ready")
        
        logger.info(f"\nARCHITECTURAL STYLE CLASSIFICATION:")
        style_field = 'Architectural Style'
        if style_field in field_stats:
            stats = field_stats[style_field]
            logger.info(f"   - {stats['unique_values']} unique styles")
            logger.info(f"   - {stats['missing_pct']:.1f}% missing data")
            logger.info(f"   - Top styles:")
            for value, count in stats['top_values'][:5]:
                logger.info(f"     * {value}: {count} examples")
    
    else:
        logger.info(f"\nALL TASKS ANALYSIS:")
        logger.info(f"   - Ready: {len(ready_fields)} fields")
        logger.info(f"   - Warning: {len(warning_fields)} fields")
        logger.info(f"   - Not ready: {len(not_ready_fields)} fields")
    
    logger.info(f"\nDATA SPLIT STRATEGY:")
    logger.info(f"   - Total buildings with images: {len(buildings_with_images)}")
    logger.info(f"   - Recommended split:")
    logger.info(f"     * Train: {int(len(buildings_with_images) * 0.7)} buildings (70%)")
    logger.info(f"     * Val: {int(len(buildings_with_images) * 0.15)} buildings (15%)")
    logger.info(f"     * Test: {int(len(buildings_with_images) * 0.15)} buildings (15%)")
    logger.info(f"   - Use stratified sampling on 'Architectural Style'")
    
    logger.info(f"\n4. NEXT STEPS:")
    logger.info(f"   1. Create PyTorch Dataset class using this analysis")
    logger.info(f"   2. Implement train/val/test split (stratified by style)")
    logger.info(f"   3. Start Phase 1 training on {len(ready_fields)} ready fields")
    logger.info(f"   4. Defer Phase 4 (alterations) - only {len([f for f in TARGET_FIELDS['very_hard'] if f in ready_fields])} fields ready")
    
    return {
        'total_buildings': len(all_buildings),
        'buildings_with_images': len(buildings_with_images),
        'field_stats': field_stats,
        'ready_fields': ready_fields,
        'warning_fields': warning_fields,
        'not_ready_fields': not_ready_fields,
        'buildings_by_style': buildings_by_style,
        'image_folders': image_folders
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Analyze image dataset for multi-task learning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase 1 analysis (Tier 1 tasks only)
  python scripts/analyze_image_data.py --phase phase1 --data-dir data/
  
  # Phase 2 analysis (Tier 1 + Tier 2 tasks)
  python scripts/analyze_image_data.py --phase phase2 --data-dir data2/
  
  # Full analysis (all fields)
  python scripts/analyze_image_data.py --data-dir data/
        """
    )
    
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('data'),
        help='Path to data directory (default: data/)'
    )
    
    parser.add_argument(
        '--phase',
        choices=['phase1', 'phase2', 'all'],
        default='phase1',
        help='Which phase to analyze (default: phase1)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Save JSON report to file (optional)'
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
    if not args.data_dir.exists():
        logger.error(f"Data directory not found: {args.data_dir}")
        sys.exit(1)
    
    logger.info(f"Analyzing dataset in: {args.data_dir}")
    logger.info(f"Phase: {args.phase}")
    
    results = analyze_dataset(args.data_dir, phase=args.phase, output_json=args.output)
    
    # Save JSON report if requested
    if args.output and results:
        logger.info(f"\nSaving analysis report to: {args.output}")
        
        # Convert to JSON-serializable format
        json_results = {
            'data_dir': str(args.data_dir),
            'phase': args.phase,
            'total_buildings': results['total_buildings'],
            'buildings_with_images': results['buildings_with_images'],
            'ready_fields': results['ready_fields'],
            'warning_fields': results['warning_fields'],
            'not_ready_fields': results['not_ready_fields'],
            'field_stats': {
                field: {
                    'total_records': stats['total_records'],
                    'missing': stats['missing'],
                    'missing_pct': stats['missing_pct'],
                    'unique_values': stats['unique_values'],
                    'top_values': [(str(v), c) for v, c in stats['top_values']]
                }
                for field, stats in results['field_stats'].items()
            }
        }
        
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        logger.info(f"✓ Report saved: {args.output}")
    
    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nNext: {'Build Track 1 preprocessing + Track 2 baseline' if args.phase == 'phase1' else 'Switch to cropped images + add Tier 2 tasks'}")
