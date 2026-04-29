"""
Run image preprocessing pipeline with Mask R-CNN detector.

This script runs the Mask R-CNN building detection pipeline on the image dataset,
generates comparison reports, and metadata files.

Usage:
    python scripts/run_preprocessing_comparison.py
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.image_preprocessing import (
    MaskRCNNDetector,
    QualityAnalyzer,
    ImageAligner,
    ComparisonRunner,
)


def find_images_in_data_directory(data_dir: str = "data") -> list:
    """
    Find all image files in the /data directory.
    
    Args:
        data_dir: Path to data directory
        
    Returns:
        List of image file paths
    """
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    image_paths = []
    
    # Find images in Photos subdirectories
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                image_paths.append(os.path.join(root, file))
    
    logger.info(f"Found {len(image_paths)} images in {data_dir}")
    return sorted(image_paths)


def main():
    """Run the preprocessing comparison pipeline."""
    
    # Configuration
    data_dir = "data"
    output_dir = "data/preprocessed_comparison"
    
    logger.info("="*70)
    logger.info("Image Preprocessing Detector Comparison")
    logger.info("="*70)
    
    # Find images
    image_paths = find_images_in_data_directory(data_dir)
    if not image_paths:
        logger.error(f"No images found in {data_dir}")
        return
    
    # Process ALL images (remove limit for full run)
    logger.info(f"Processing {len(image_paths)} images from {data_dir}")

    
    # Initialize detector
    logger.info("\nInitializing Mask R-CNN detector...")
    
    try:
        mask_rcnn_detector = MaskRCNNDetector(
            model_name="mask-rcnn",
            device="cpu",
            confidence_threshold=0.5,
            min_building_area_ratio=0.05,
            max_building_area_ratio=0.95,
        )
        mask_rcnn_detector.display_name = "Mask R-CNN (Building Detection)"
        logger.info("✓ Mask R-CNN detector initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Mask R-CNN: {e}")
        logger.error("Make sure Detectron2 is installed: pip install detectron2")
        return
    
    # Prepare detectors list (only Mask R-CNN)
    detectors = [mask_rcnn_detector]
    
    # Initialize quality analyzer and aligner
    quality_analyzer = QualityAnalyzer()
    image_aligner = ImageAligner()
    
    # Run comparison
    try:
        runner = ComparisonRunner(
            detectors=detectors,
            output_dir=output_dir,
            quality_analyzer=quality_analyzer,
            image_aligner=image_aligner,
        )
        
        logger.info(f"\nStarting comparison on {len(image_paths)} images...")
        logger.info(f"Output directory: {output_dir}\n")
        
        results = runner.run_comparison(image_paths)
        
        # Save results
        logger.info("\nSaving results...")
        runner.save_results()
        
        # Generate HTML report
        html_path = runner.generate_html_report()
        logger.info(f"✓ HTML report generated: {html_path}")
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("COMPARISON SUMMARY")
        logger.info("="*70)
        for detector_name, result_data in results.items():
            logger.info(f"\n{detector_name}:")
            for key, value in result_data["summary"].items():
                logger.info(f"  {key}: {value}")
        
        logger.info("\n✓ Preprocessing comparison complete!")
        logger.info(f"Open the HTML report to view results: file://{os.path.abspath(html_path)}")
        
    except Exception as e:
        logger.error(f"Error running comparison: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
