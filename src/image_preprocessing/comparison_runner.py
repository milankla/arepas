"""Comparison runner for side-by-side detector evaluation."""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List
from loguru import logger
import base64

from .pipeline import PreprocessingPipeline
from .detector_base import BaseDetector
from .quality_analyzer import QualityAnalyzer
from .image_aligner import ImageAligner


class ComparisonRunner:
    """Run side-by-side comparison of multiple detectors."""
    
    def __init__(
        self,
        detectors: List[BaseDetector],
        output_dir: str,
        quality_analyzer: QualityAnalyzer = None,
        image_aligner: ImageAligner = None,
    ):
        """
        Initialize comparison runner.
        
        Args:
            detectors: List of detector instances to compare
            output_dir: Directory for all output files
            quality_analyzer: Quality analyzer instance
            image_aligner: Image aligner instance
        """
        self.detectors = detectors
        self.output_dir = output_dir
        self.quality_analyzer = quality_analyzer or QualityAnalyzer()
        self.image_aligner = image_aligner or ImageAligner()
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.results = {}
        self.comparison_metadata = []
    
    def run_comparison(self, image_paths: List[str]) -> Dict:
        """
        Run all detectors on same image set.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            Comparison results
        """
        logger.info(f"Starting detector comparison on {len(image_paths)} images")
        logger.info(f"Comparing detectors: {[d.model_name for d in self.detectors]}")
        
        total_start = time.time()
        
        for detector in self.detectors:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing with detector: {detector.model_name}")
            logger.info(f"{'='*60}\n")
            
            # Create detector-specific output directory
            detector_output_dir = os.path.join(self.output_dir, detector.model_name)
            os.makedirs(detector_output_dir, exist_ok=True)
            
            # Create and run pipeline
            pipeline = PreprocessingPipeline(
                detector=detector,
                output_dir=detector_output_dir,
                quality_analyzer=self.quality_analyzer,
                image_aligner=self.image_aligner,
            )
            
            stats = pipeline.process_images(image_paths)
            pipeline.save_metadata(
                os.path.join(detector_output_dir, "metadata.json")
            )
            
            self.results[detector.model_name] = {
                "stats": stats,
                "summary": pipeline.get_summary(),
                "output_dir": detector_output_dir,
                "metadata": pipeline.metadata,
                "display_name": getattr(detector, "display_name", detector.model_name),
            }
            
            display_name = getattr(detector, "display_name", detector.model_name)
            logger.info(f"\n{display_name} Summary:")
            for key, value in pipeline.get_summary().items():
                logger.info(f"  {key}: {value}")
        
        total_time = time.time() - total_start
        logger.info(f"\nTotal processing time: {total_time:.1f} seconds")
        
        return self.results
    
    def generate_html_report(self, output_path: str = None) -> str:
        """
        Generate HTML comparison report with side-by-side visualization.
        
        Args:
            output_path: Path to save HTML report
            
        Returns:
            Path to generated HTML file
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, "comparison_report.html")
        
        logger.info(f"Generating HTML comparison report")
        
        # Extract comparison data
        comparison_data = self._prepare_comparison_data()
        
        html_content = self._generate_html(comparison_data)
        
        with open(output_path, "w") as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to {output_path}")
        return output_path
    
    def _prepare_comparison_data(self) -> List[Dict]:
        """Prepare data for HTML visualization."""
        comparison_data = []
        
        detector_names = list(self.results.keys())
        all_metadata = {}
        
        for detector_name in detector_names:
            metadata_list = self.results[detector_name]["metadata"]
            all_metadata[detector_name] = {
                m["source_image"]: m for m in metadata_list
            }
        
        # Get unique source images
        all_sources = set()
        for detector_metadata in all_metadata.values():
            all_sources.update(detector_metadata.keys())
        
        for source_image in sorted(all_sources):
            image_comparison = {
                "source_image": source_image,
                "detectors": {}
            }
            
            for detector_name in detector_names:
                metadata = all_metadata[detector_name].get(source_image, {})
                image_comparison["detectors"][detector_name] = metadata
            
            comparison_data.append(image_comparison)
        
        return comparison_data
    
    def _generate_html(self, comparison_data: List[Dict]) -> str:
        """Generate HTML content."""
        detector_names = list(self.results.keys())
        
        # Generate summary table
        summary_html = self._generate_summary_table()
        
        # Generate comparison rows
        comparison_rows = []
        for i, item in enumerate(comparison_data):
            if i >= 20:  # Limit to first 20 images for performance
                break
            row = self._generate_comparison_row(item, detector_names)
            comparison_rows.append(row)
        
        comparison_html = "\n".join(comparison_rows)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Image Preprocessing Detector Comparison</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #0066cc;
            margin-top: 30px;
        }}
        .summary {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #0066cc;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        .comparison-row {{
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .detector-column {{
            float: left;
            width: calc(24% - 15px);
            margin-right: 15px;
            text-align: center;
        }}
        .image-stage {{
            margin: 8px 0;
            padding: 8px;
            background-color: #e8f4f8;
            border-left: 3px solid #0066cc;
            border-radius: 3px;
        }}
        .image-stage-title {{
            font-size: 10px;
            font-weight: bold;
            color: #0066cc;
            margin-bottom: 3px;
            text-transform: uppercase;
        }}
        .detector-column img {{
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 3px;
            margin: 10px 0;
        }}
        .detector-column h4 {{
            margin: 10px 0 5px 0;
            color: #0066cc;
        }}
        .detector-column p {{
            font-size: 12px;
            color: #666;
            margin: 3px 0;
        }}
        .metrics {{
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 3px;
            font-size: 11px;
            margin-top: 10px;
        }}
        .metric-label {{
            font-weight: bold;
            color: #333;
        }}
        .pass {{
            color: green;
            font-weight: bold;
        }}
        .fail {{
            color: red;
            font-weight: bold;
        }}
        .clearfix::after {{
            content: " ";
            display: table;
            clear: both;
        }}
        .detector-name {{
            background-color: #e6f2ff;
            padding: 5px;
            border-radius: 3px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>🏗️ Image Preprocessing Detector Comparison Report</h1>
    <p>Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary Statistics</h2>
    {summary_html}
    
    <h2>Side-by-Side Comparison (First 20 Images)</h2>
    <p>Each row shows the same source image processed by different detectors.</p>
    
    {comparison_html}
    
</body>
</html>
"""
        return html
    
    def _generate_summary_table(self) -> str:
        """Generate summary statistics table."""
        rows = []
        rows.append("<table>")
        rows.append("<th>Detector</th>")
        rows.append("<th>Total Images</th>")
        rows.append("<th>Detection Rate</th>")
        rows.append("<th>Quality Pass Rate</th>")
        rows.append("<th>Alignment Rate</th>")
        rows.append("<th>Success Rate</th>")
        rows.append("<th>Processing Time</th>")
        rows.append("</tr>")
        
        for detector_name, result_data in self.results.items():
            summary = result_data["summary"]
            stats = result_data["stats"]
            display_name = result_data.get("display_name", detector_name)
            
            rows.append("<tr>")
            rows.append(f"<td><strong>{display_name}</strong></td>")
            rows.append(f"<td>{summary.get('total_images', 'N/A')}</td>")
            rows.append(f"<td>{summary.get('detection_rate', 'N/A')}</td>")
            rows.append(f"<td>{summary.get('quality_pass_rate', 'N/A')}</td>")
            rows.append(f"<td>{summary.get('alignment_rate', 'N/A')}</td>")
            rows.append(f"<td>{summary.get('final_success_rate', 'N/A')}</td>")
            rows.append(f"<td>{summary.get('processing_time_seconds', 0):.1f}s</td>")
            rows.append("</tr>")
        
        rows.append("</table>")
        return "\n".join(rows)
    
    def _generate_comparison_row(self, item: Dict, detector_names: List[str]) -> str:
        """Generate a single comparison row with original → cropped → aligned stages."""
        source_image = item["source_image"]
        
        row_html = [f'<div class="comparison-row">']
        row_html.append(f'<h3>Source: {Path(source_image).name}</h3>')
        row_html.append('<div class="clearfix">')
        
        # Show ORIGINAL source image first (column 1)
        row_html.append('<div class="detector-column">')
        row_html.append('<h4 class="detector-name" style="background-color:#fff3cd;">📷 Original</h4>')
        if os.path.exists(source_image):
            file_url = self._path_to_file_url(source_image)
            row_html.append(f'<img src="{file_url}" alt="Original" style="max-height: 220px">')
        else:
            row_html.append('<p class="fail">❌ Original image not found</p>')
        row_html.append('</div>')
        
        # Show detector results (columns 2+)
        for detector_name in detector_names:
            metadata = item["detectors"].get(detector_name, {})
            
            # Get display name for this detector
            detector_display_name = detector_name
            for result_name, result_data in self.results.items():
                if result_name == detector_name:
                    detector_display_name = result_data.get("display_name", detector_name)
                    break
            
            row_html.append('<div class="detector-column">')
            row_html.append(f'<h4 class="detector-name">{detector_display_name}</h4>')
            
            status = metadata.get("status", "unknown")
            detected = metadata.get("detected", False)
            
            if status == "success" and detected:
                cropped_path = metadata.get("cropped_image")
                aligned_path = metadata.get("aligned_image")
                
                # Show cropped building
                if cropped_path and os.path.exists(cropped_path):
                    row_html.append('<div class="image-stage">')
                    row_html.append('<div class="image-stage-title">🔍 Cropped</div>')
                    file_url = self._path_to_file_url(cropped_path)
                    row_html.append(f'<img src="{file_url}" alt="Cropped" style="max-height: 140px">')
                    row_html.append('</div>')
                
                # Show aligned image
                if aligned_path and os.path.exists(aligned_path):
                    row_html.append('<div class="image-stage">')
                    row_html.append('<div class="image-stage-title">✨ Aligned (512x512)</div>')
                    file_url = self._path_to_file_url(aligned_path)
                    row_html.append(f'<img src="{file_url}" alt="Aligned" style="max-height: 140px">')
                    row_html.append('</div>')
                
                # Show metrics
                row_html.append('<div class="metrics">')
                row_html.append(f'<p><span class="metric-label">Quality:</span> ' +
                               f'<span class="pass">{metadata.get("quality_flag", "N/A")}</span></p>')
                row_html.append(f'<p><span class="metric-label">Score:</span> {metadata.get("quality_score", 0):.1f}</p>')
                row_html.append(f'<p><span class="metric-label">Size:</span> {metadata.get("width", 0)}x{metadata.get("height", 0)}</p>')
                row_html.append(f'<p><span class="metric-label">Brightness:</span> {metadata.get("brightness", 0):.0f}</p>')
                row_html.append(f'<p><span class="metric-label">Blur:</span> {metadata.get("blur_score", 0):.1f}</p>')
                row_html.append('</div>')
            else:
                reason = metadata.get("status", "unknown")
                error = metadata.get("error", "")
                row_html.append(f'<p class="fail">❌ {reason}</p>')
                if error:
                    row_html.append(f'<p><small>{error[:100]}</small></p>')
            
            row_html.append('</div>')
        
        row_html.append('</div>')
        row_html.append('</div>')
        
        return "\n".join(row_html)
    
    def _path_to_file_url(self, file_path: str) -> str:
        """Convert file path to file:// URL (macOS/Linux/Windows compatible)."""
        # Get absolute path - handles both absolute and relative paths
        abs_path = os.path.abspath(file_path)
        
        # On Windows, os.path.abspath returns paths like C:\Users\...\file.jpg
        # On macOS/Linux, it returns /Users/.../file.jpg
        # The file:// URL format needs:
        # - Windows: file:///C:/Users/.../file.jpg
        # - macOS/Linux: file:///Users/.../file.jpg
        
        if sys.platform == "win32":
            # Windows: Convert backslashes to forward slashes and add file:/// prefix
            file_url = "file:///" + abs_path.replace("\\", "/")
        else:
            # macOS and Linux: Just add file:// prefix (path already starts with /)
            file_url = "file://" + abs_path
        
        return file_url
    
    def save_results(self, output_path: str = None):
        """Save detailed results to JSON."""
        if output_path is None:
            output_path = os.path.join(self.output_dir, "comparison_results.json")
        
        # Prepare data for JSON serialization
        serializable_results = {}
        for detector_name, result_data in self.results.items():
            serializable_results[detector_name] = {
                "summary": result_data["summary"],
                "stats": result_data["stats"],
                "metadata_count": len(result_data["metadata"]),
            }
        
        with open(output_path, "w") as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Comparison results saved to {output_path}")
