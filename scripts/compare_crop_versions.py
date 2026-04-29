"""
Compare crops generated with old vs new parameters.
Shows original image, old crop (10% padding, 70% size), and new crop (5% padding, 55% center).
"""

import os
import json
from pathlib import Path
from loguru import logger

def find_sample_images(data_dir: str = "data", num_samples: int = 3) -> list:
    """Find sample image files across different architectural styles."""
    samples = []
    
    # Get images from each architectural style
    style_dirs = ["Bungalows", "Minimal Traditional"]
    
    for style in style_dirs:
        style_path = os.path.join(data_dir, style, f"{style} - Photos")
        if not os.path.isdir(style_path):
            continue
        
        # Get images directly from the style path
        images = [f for f in os.listdir(style_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Take samples from this style
        for img in images[:3]:  # Get 3 images per style
            sample_image = os.path.join(style_path, img)
            samples.append({
                'original': sample_image,
                'style': style,
                'building': img.split('_')[1] if '_' in img else img.split('.')[0]
            })
            
            if len(samples) >= num_samples:
                return samples
    
    return samples[:num_samples]


def get_cropped_filename(original_path: str) -> str:
    """Generate the cropped filename from original image path."""
    # Remove directory structure and use original filename
    return Path(original_path).stem + "_cropped.jpg"


def create_comparison_html(samples: list, output_path: str = "data/preprocessed/comparison_versions.html"):
    """Create HTML comparing original, old crop, and new crop versions."""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crop Parameter Comparison - Old vs New</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.95;
        }
        
        .params-comparison {
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .params-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 30px;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        
        .params-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        
        .param-label {
            font-weight: 600;
            color: #333;
            font-size: 1.1em;
        }
        
        .param-old {
            background: #fff3cd;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        
        .param-new {
            background: #d4edda;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }
        
        .param-old h4, .param-new h4 {
            font-size: 0.9em;
            opacity: 0.7;
            margin-bottom: 5px;
        }
        
        .param-value {
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }
        
        .sample-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
            margin-bottom: 50px;
        }
        
        .sample-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .sample-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .sample-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: center;
        }
        
        .sample-header h3 {
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        
        .sample-header p {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .sample-image {
            width: 100%;
            height: 300px;
            object-fit: cover;
            background: #f0f0f0;
        }
        
        .image-not-found {
            width: 100%;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f0f0f0;
            color: #999;
            font-size: 0.9em;
            text-align: center;
            padding: 20px;
        }
        
        .sample-label {
            background: #f8f9fa;
            padding: 12px;
            text-align: center;
            border-top: 1px solid #eee;
            font-weight: 500;
            color: #666;
            font-size: 0.95em;
        }
        
        .sample-label.original {
            background: #e3f2fd;
            color: #1976d2;
        }
        
        .sample-label.old {
            background: #fff3cd;
            color: #856404;
        }
        
        .sample-label.new {
            background: #d4edda;
            color: #155724;
        }
        
        .comparison-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 40px;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .comparison-item {
            display: flex;
            flex-direction: column;
        }
        
        .comparison-item-title {
            font-weight: 600;
            margin-bottom: 10px;
            text-align: center;
            font-size: 1.05em;
        }
        
        .comparison-item-original .comparison-item-title {
            color: #1976d2;
        }
        
        .comparison-item-old .comparison-item-title {
            color: #f57c00;
        }
        
        .comparison-item-new .comparison-item-title {
            color: #388e3c;
        }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px solid rgba(255,255,255,0.3);
        }
        
        .footer p {
            font-size: 0.95em;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Building Crop Parameter Comparison</h1>
            <p>Visual comparison of crops with old vs new preprocessing parameters</p>
        </div>
        
        <div class="params-comparison">
            <div class="params-row">
                <div class="param-label">Parameter</div>
                <div class="param-label">Old Settings</div>
                <div class="param-label">New Settings</div>
            </div>
            
            <div class="params-row">
                <div class="param-label">Padding</div>
                <div class="param-old">
                    <h4>OLD</h4>
                    <div class="param-value">10%</div>
                </div>
                <div class="param-new">
                    <h4>NEW</h4>
                    <div class="param-value">5%</div>
                </div>
            </div>
            
            <div class="params-row">
                <div class="param-label">Size Weight</div>
                <div class="param-old">
                    <h4>OLD</h4>
                    <div class="param-value">70%</div>
                </div>
                <div class="param-new">
                    <h4>NEW</h4>
                    <div class="param-value">45%</div>
                </div>
            </div>
            
            <div class="params-row">
                <div class="param-label">Position Weight (Center Bias)</div>
                <div class="param-old">
                    <h4>OLD</h4>
                    <div class="param-value">30%</div>
                </div>
                <div class="param-new">
                    <h4>NEW</h4>
                    <div class="param-value">55%</div>
                </div>
            </div>
            
            <div class="params-row">
                <div class="param-label">Result</div>
                <div class="param-old">
                    <h4>OLD</h4>
                    <p style="color: #666; font-size: 0.95em;">Prefers large buildings regardless of position</p>
                </div>
                <div class="param-new">
                    <h4>NEW</h4>
                    <p style="color: #666; font-size: 0.95em;">Prefers centered buildings, tighter crops</p>
                </div>
            </div>
        </div>
"""
    
    # Add comparison rows for each sample
    html_content += "        <h2 style=\"color: white; margin-bottom: 30px; text-align: center;\">Sample Comparisons</h2>\n"
    
    for i, sample in enumerate(samples, 1):
        original = sample['original']
        style = sample['style']
        building = sample['building']
        cropped_filename = get_cropped_filename(original)
        old_crop = f"data/preprocessed/cropped_old/{cropped_filename}"
        new_crop = f"data/preprocessed/cropped/{cropped_filename}"
        
        html_content += f"""
        <div class="comparison-row">
            <div class="comparison-item comparison-item-original">
                <div class="comparison-item-title">Original Image</div>
                <div class="comparison-item-body">
                    <strong style="color: #666; display: block; margin-bottom: 8px; font-size: 0.9em;">
                        {style} - {building}
                    </strong>
"""
        
        # Check original image exists
        if os.path.isfile(original):
            html_content += f'                    <img src="../../{original}" class="sample-image" alt="Original">'
        else:
            html_content += f'                    <div class="image-not-found">File not found</div>'
        
        html_content += f"""
                </div>
            </div>
            
            <div class="comparison-item comparison-item-old">
                <div class="comparison-item-title">Old Crop (10% pad, 70% size)</div>
"""
        
        # Check old crop exists
        if os.path.isfile(old_crop):
            html_content += f'                <img src="../../{old_crop}" class="sample-image" alt="Old Crop">'
        else:
            html_content += f'                <div class="image-not-found">Processing...</div>'
        
        html_content += f"""
            </div>
            
            <div class="comparison-item comparison-item-new">
                <div class="comparison-item-title">New Crop (5% pad, 55% center)</div>
"""
        
        # Check new crop exists
        if os.path.isfile(new_crop):
            html_content += f'                <img src="../../{new_crop}" class="sample-image" alt="New Crop">'
        else:
            html_content += f'                <div class="image-not-found">Processing...</div>'
        
        html_content += f"""
            </div>
        </div>
"""
    
    html_content += """
        <div class="footer">
            <p>Processing in progress... Page will refresh with new crops as they become available.</p>
        </div>
    </div>
</body>
</html>
"""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    logger.info(f"✓ Comparison HTML created: {output_path}")
    return output_path


if __name__ == "__main__":
    samples = find_sample_images(num_samples=3)
    
    if samples:
        for sample in samples:
            logger.info(f"Sample: {sample['style']} - {sample['building']}")
            logger.info(f"  Original: {sample['original']}")
        
        html_path = create_comparison_html(samples)
        logger.info(f"\n✓ Comparison HTML ready: {html_path}")
    else:
        logger.error("No sample images found")
