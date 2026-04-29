"""Generate before/after HTML comparison for building detection."""

import os
import re
from pathlib import Path

# Paths
data_dir = "/Users/ozaklanjsek/Downloads/arepas/data"
cropped_dir = os.path.join(data_dir, "preprocessed", "cropped")
output_file = os.path.join(data_dir, "preprocessed", "before_after_comparison.html")

# Find all cropped images and match them with originals
cropped_images = sorted([f for f in os.listdir(cropped_dir) if f.endswith('_cropped.jpg')])

# Extract base names and find originals
pairs = []
for cropped_name in cropped_images:
    # Remove '_cropped' suffix to get the original base name
    base_name = cropped_name.replace('_cropped.jpg', '.jpg')
    
    # Search in both folders
    original_path = None
    for category in ["Bungalows", "Minimal Traditional"]:
        search_path = os.path.join(data_dir, category, f"{category} - Photos", base_name)
        if os.path.exists(search_path):
            original_path = search_path
            category_name = category
            break
    
    if original_path:
        cropped_path = os.path.join(cropped_dir, cropped_name)
        pairs.append({
            'original': original_path,
            'cropped': cropped_path,
            'original_name': base_name,
            'cropped_name': cropped_name,
            'category': category_name,
        })

print(f"Found {len(pairs)} before/after image pairs")

# Generate HTML
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Building Detection: Before & After</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        header p {
            font-size: 1.1em;
            opacity: 0.95;
        }
        
        .stats {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 40px;
            display: flex;
            justify-content: space-around;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .comparison-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .comparison-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .comparison-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0;
        }
        
        .image-section {
            position: relative;
            overflow: hidden;
            background: #f5f5f5;
            aspect-ratio: 1 / 1;
        }
        
        .image-section img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
        }
        
        .label {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 0.9em;
            font-weight: bold;
            z-index: 10;
        }
        
        .label.before {
            background: rgba(0, 150, 136, 0.8);
        }
        
        .label.after {
            background: rgba(76, 175, 80, 0.8);
        }
        
        .card-info {
            padding: 15px;
            background: #f9f9f9;
            border-top: 1px solid #eee;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
            font-size: 0.9em;
        }
        
        .info-label {
            font-weight: 600;
            color: #333;
        }
        
        .info-value {
            color: #666;
        }
        
        .category-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .category-badge.bungalows {
            background: #e8f5e9;
            color: #2e7d32;
        }
        
        .category-badge.minimal {
            background: #f3e5f5;
            color: #6a1b9a;
        }
        
        footer {
            text-align: center;
            color: white;
            margin-top: 50px;
            padding: 20px;
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            .comparison-content {
                grid-template-columns: 1fr;
            }
            
            header h1 {
                font-size: 1.8em;
            }
            
            .gallery {
                grid-template-columns: 1fr;
            }
            
            .stats {
                flex-direction: column;
                gap: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏠 Building Detection Comparison</h1>
            <p>Before and After - Faster R-CNN Bounding Box Extraction</p>
        </header>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">STAT_TOTAL</div>
                <div class="stat-label">Image Pairs</div>
            </div>
            <div class="stat">
                <div class="stat-number">STAT_BUNGALOW</div>
                <div class="stat-label">Bungalows</div>
            </div>
            <div class="stat">
                <div class="stat-number">STAT_MINIMAL</div>
                <div class="stat-label">Minimal Traditional</div>
            </div>
        </div>
        
        <div class="gallery">
"""

# Count by category
bungalow_count = sum(1 for p in pairs if p['category'] == 'Bungalows')
minimal_count = sum(1 for p in pairs if p['category'] == 'Minimal Traditional')

# Add first 30 pairs to HTML (or all if fewer)
display_pairs = pairs[:30]

for pair in display_pairs:
    category = pair['category']
    badge_class = 'bungalows' if category == 'Bungalows' else 'minimal'
    
    # Get relative paths for display in HTML
    original_rel = os.path.relpath(pair['original'], os.path.dirname(output_file))
    cropped_rel = os.path.relpath(pair['cropped'], os.path.dirname(output_file))
    
    html_content += f"""            <div class="comparison-card">
                <div class="comparison-content">
                    <div class="image-section">
                        <span class="label before">BEFORE</span>
                        <img src="{original_rel}" alt="Original image">
                    </div>
                    <div class="image-section">
                        <span class="label after">AFTER</span>
                        <img src="{cropped_rel}" alt="Cropped image">
                    </div>
                </div>
                <div class="card-info">
                    <div class="info-row">
                        <span class="category-badge {badge_class}">{category}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Original:</span>
                        <span class="info-value">{pair['original_name']}</span>
                    </div>
                </div>
            </div>
"""

html_content += """        </div>
        
        <footer>
            <p>Faster R-CNN (PyTorch/Torchvision) - Precise building detection and cropping</p>
            <p>Generated on April 27, 2026</p>
        </footer>
    </div>
</body>
</html>
"""

# Replace placeholders safely to avoid CSS brace conflicts
html_content = html_content.replace('STAT_TOTAL', str(len(pairs)))
html_content = html_content.replace('STAT_BUNGALOW', str(bungalow_count))
html_content = html_content.replace('STAT_MINIMAL', str(minimal_count))

# Write HTML file
with open(output_file, 'w') as f:
    f.write(html_content)

print(f"✓ HTML file created: {output_file}")
print(f"  Displaying first {len(display_pairs)} pairs out of {len(pairs)} total")
print(f"  Categories: {bungalow_count} Bungalows, {minimal_count} Minimal Traditional")
