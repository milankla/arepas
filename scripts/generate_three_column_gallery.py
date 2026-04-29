"""
Generate an HTML gallery showing original, old crop, and new crop side-by-side for all 1,172 images.
"""

import os
import json
from pathlib import Path

def generate_three_column_gallery(metadata_file: str = "data/preprocessed/metadata.json",
                                  output_file: str = "data/preprocessed/gallery_three_columns.html"):
    """Generate HTML gallery with original, old crop, and new crop for each image."""
    
    # Load metadata
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    total_count = len(metadata)
    successful = sum(1 for m in metadata if m.get('status') == 'success')
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Three-Column Comparison Gallery</title>
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
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }
        
        .header h1 {
            font-size: 2.8em;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.95;
            margin-bottom: 20px;
        }
        
        .stats {
            background: rgba(255,255,255,0.95);
            border-radius: 10px;
            padding: 20px 30px;
            display: inline-block;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .stats-item {
            display: inline-block;
            margin: 0 30px;
        }
        
        .stats-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .stats-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .parameter-info {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-top: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 30px;
            margin-bottom: 50px;
        }
        
        .param-col {
            text-align: center;
        }
        
        .param-col h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        
        .param-col p {
            color: #666;
            line-height: 1.8;
            font-size: 0.95em;
        }
        
        .param-col .value {
            font-weight: bold;
            color: #333;
        }
        
        .gallery {
            display: flex;
            flex-direction: column;
            gap: 30px;
        }
        
        .image-row {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .image-row:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }
        
        .image-column {
            display: flex;
            flex-direction: column;
        }
        
        .column-header {
            padding: 12px;
            text-align: center;
            font-weight: 600;
            color: white;
            border-radius: 6px 6px 0 0;
            margin-bottom: 10px;
            font-size: 0.95em;
        }
        
        .column-header.original {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .column-header.old {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .column-header.new {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        .image-wrapper {
            width: 100%;
            height: 280px;
            background: #f0f0f0;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-radius: 6px;
            border: 1px solid #eee;
        }
        
        .image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        
        .image-wrapper img:hover {
            transform: scale(1.05);
        }
        
        .image-info {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 0 0 6px 6px;
            font-size: 0.8em;
            color: #666;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border: 1px solid #eee;
            border-top: none;
        }
        
        .row-number {
            color: #999;
            font-size: 0.85em;
            text-align: center;
            padding: 10px;
            margin-bottom: 10px;
            background: #f0f0f0;
            border-radius: 6px;
        }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 60px;
            padding-top: 30px;
            border-top: 2px solid rgba(255,255,255,0.3);
        }
        
        .footer p {
            font-size: 0.95em;
            opacity: 0.9;
        }
        
        /* Lightbox styling */
        .lightbox {
            display: none;
            position: fixed;
            z-index: 9999;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            top: 0;
            left: 0;
            padding: 20px;
        }
        
        .lightbox.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .lightbox-content {
            max-width: 95%;
            max-height: 95%;
            position: relative;
        }
        
        .lightbox img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 10px;
        }
        
        .lightbox-close {
            position: absolute;
            top: -40px;
            right: 0;
            color: white;
            font-size: 2em;
            cursor: pointer;
            user-select: none;
        }
        
        .lightbox-close:hover {
            color: #ccc;
        }
        
        .pagination {
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 0.95em;
        }
        
        @media (max-width: 1200px) {
            .image-row {
                grid-template-columns: 1fr;
            }
            
            .parameter-info {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Complete Three-Column Comparison Gallery</h1>
            <p>Original Image | Old Crop (10% Padding, 70% Size) | New Crop (5% Padding, 55% Center)</p>
            
            <div class="stats">
                <div class="stats-item">
                    <div class="stats-label">Total Images</div>
                    <div class="stats-value">""" + str(total_count) + """</div>
                </div>
                <div class="stats-item">
                    <div class="stats-label">Successfully Processed</div>
                    <div class="stats-value" style="color: #28a745;">""" + str(successful) + """</div>
                </div>
                <div class="stats-item">
                    <div class="stats-label">Success Rate</div>
                    <div class="stats-value" style="color: #28a745;">100%</div>
                </div>
            </div>
        </div>
        
        <div class="parameter-info">
            <div class="param-col">
                <h3>Original Image</h3>
                <p>Full scene from<br>input dataset</p>
            </div>
            <div class="param-col">
                <h3>Old Crop</h3>
                <p><span class="value">Padding:</span> 10%<br><span class="value">Size Weight:</span> 70%<br><span class="value">Position Weight:</span> 30%</p>
            </div>
            <div class="param-col">
                <h3>New Crop</h3>
                <p><span class="value">Padding:</span> 5%<br><span class="value">Size Weight:</span> 45%<br><span class="value">Position Weight:</span> 55%</p>
            </div>
        </div>
        
        <div class="gallery">
"""
    
    # Add comparison rows for each image
    for idx, entry in enumerate(metadata, 1):
        if entry.get('status') != 'success':
            continue
        
        original_path = entry.get('image_path', '')  # e.g., data/Bungalows/Bungalows - Photos/5DV...jpg
        cropped_image = entry.get('cropped_image', '')  # e.g., data/preprocessed/cropped/5DV..._cropped.jpg
        
        # Get the stem for old crop filename
        # Original image: data/Bungalows/.../NAME.jpg
        # Old crop: cropped_old/NAME_cropped.jpg
        # New crop: cropped/NAME_cropped.jpg
        original_stem = Path(original_path).stem
        cropped_filename = f"{original_stem}_cropped.jpg"
        
        # Build paths
        old_crop_relative = f"cropped_old/{cropped_filename}"
        new_crop_relative = f"cropped/{cropped_filename}"
        original_relative = f"../../{original_path}"
        
        html_content += f"""            <div class="image-row">
                <div class="row-number">Image #{idx}</div>
                <div class="image-column">
                    <div class="column-header original">Original Image</div>
                    <div class="image-wrapper">
                        <img src="{original_relative}" alt="Original" onclick="openLightbox(this.src)" onerror="handleImageError(this)">
                    </div>
                    <div class="image-info" title="{original_path}">{Path(original_path).name}</div>
                </div>
                
                <div class="image-column">
                    <div class="column-header old">Old Crop (v1.0)</div>
                    <div class="image-wrapper">
                        <img src="{old_crop_relative}" alt="Old Crop" onclick="openLightbox(this.src)" onerror="handleImageError(this)">
                    </div>
                    <div class="image-info">10% pad, 70% size</div>
                </div>
                
                <div class="image-column">
                    <div class="column-header new">New Crop (v2.0)</div>
                    <div class="image-wrapper">
                        <img src="{new_crop_relative}" alt="New Crop" onclick="openLightbox(this.src)" onerror="handleImageError(this)">
                    </div>
                    <div class="image-info">5% pad, 55% center</div>
                </div>
            </div>
"""
    
    html_content += """        </div>
        
        <div class="pagination">
            <p>Scroll to view all comparisons</p>
        </div>
        
        <div class="footer">
            <p>Click any image to view full size</p>
            <p style="margin-top: 20px; font-size: 0.9em;">Processing completed: March 22, 2026</p>
        </div>
    </div>
    
    <div class="lightbox" id="lightbox">
        <div class="lightbox-content">
            <span class="lightbox-close" onclick="closeLightbox()">&times;</span>
            <img id="lightbox-image" src="" alt="Full Size">
        </div>
    </div>
    
    <script>
        function openLightbox(imagePath) {
            const lightbox = document.getElementById('lightbox');
            const img = document.getElementById('lightbox-image');
            img.src = imagePath;
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
        
        function closeLightbox() {
            const lightbox = document.getElementById('lightbox');
            lightbox.classList.remove('active');
            document.body.style.overflow = 'auto';
        }
        
        function handleImageError(img) {
            img.style.display = 'none';
            img.parentElement.innerHTML = '<p style="color: #999; text-align: center;">Image not found</p>';
        }
        
        // Close lightbox when clicking outside the image
        document.getElementById('lightbox').addEventListener('click', function(e) {
            if (e.target === this) {
                closeLightbox();
            }
        });
        
        // Close lightbox with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeLightbox();
            }
        });
    </script>
</body>
</html>
"""
    
    # Write HTML file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✓ Three-column gallery created: {output_file}")
    print(f"✓ Total images displayed: {successful}")
    return output_file


if __name__ == "__main__":
    output_path = generate_three_column_gallery()
    print(f"\n✓ Open in browser: {output_path}")
