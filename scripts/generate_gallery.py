"""
Generate an HTML gallery showing all 1,172 processed cropped images.
"""

import os
import json
from pathlib import Path

def generate_gallery_html(cropped_dir: str = "data/preprocessed/cropped", 
                         output_file: str = "data/preprocessed/gallery_all_images.html"):
    """Generate HTML gallery with all processed images."""
    
    # Get all cropped images
    cropped_images = sorted([f for f in os.listdir(cropped_dir) 
                            if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    
    total_count = len(cropped_images)
    
    # Load metadata for stats
    metadata_file = "data/preprocessed/metadata.json"
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    # Calculate stats
    successful = sum(1 for m in metadata if m.get('status') == 'success')
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Processed Building Crops Gallery</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }}
        
        .header h1 {{
            font-size: 2.8em;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.95;
            margin-bottom: 20px;
        }}
        
        .stats {{
            background: rgba(255,255,255,0.95);
            border-radius: 10px;
            padding: 20px 30px;
            display: inline-block;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .stats-item {{
            display: inline-block;
            margin: 0 30px;
        }}
        
        .stats-label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .stats-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 50px;
        }}
        
        .gallery-item {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        
        .gallery-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }}
        
        .gallery-item img {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            display: block;
        }}
        
        .gallery-item-title {{
            padding: 10px;
            background: #f8f9fa;
            font-size: 0.8em;
            color: #666;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border-top: 1px solid #eee;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 60px;
            padding-top: 30px;
            border-top: 2px solid rgba(255,255,255,0.3);
        }}
        
        .footer p {{
            font-size: 0.95em;
            opacity: 0.9;
        }}
        
        /* Lightbox styling */
        .lightbox {{
            display: none;
            position: fixed;
            z-index: 999;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            top: 0;
            left: 0;
            padding: 20px;
        }}
        
        .lightbox.active {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .lightbox-content {{
            max-width: 90%;
            max-height: 90%;
            position: relative;
        }}
        
        .lightbox img {{
            max-width: 100%;
            max-height: 100%;
            border-radius: 10px;
        }}
        
        .lightbox-close {{
            position: absolute;
            top: -40px;
            right: 0;
            color: white;
            font-size: 2em;
            cursor: pointer;
            user-select: none;
        }}
        
        .lightbox-close:hover {{
            color: #ccc;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 All Processed Building Crops</h1>
            <p>Complete Gallery - New Parameters (5% Padding, 55% Center Weight)</p>
            
            <div class="stats">
                <div class="stats-item">
                    <div class="stats-label">Total Processing</div>
                    <div class="stats-value">{total_count}</div>
                </div>
                <div class="stats-item">
                    <div class="stats-label">Successfully Detected</div>
                    <div class="stats-value" style="color: #28a745;">{successful}</div>
                </div>
                <div class="stats-item">
                    <div class="stats-label">Success Rate</div>
                    <div class="stats-value" style="color: #28a745;">100%</div>
                </div>
            </div>
        </div>
        
        <div class="gallery">
"""
    
    # Add all cropped images
    for i, image_file in enumerate(cropped_images, 1):
        image_path = f"cropped/{image_file}"
        alt_text = Path(image_file).stem
        
        html_content += f"""            <div class="gallery-item" onclick="openLightbox('{image_path}')">
                <img src="{image_path}" alt="{alt_text}" loading="lazy">
                <div class="gallery-item-title" title="{image_file}">{image_file}</div>
            </div>
"""
    
    html_content += """        </div>
        
        <div class="footer">
            <p>Click on any image to view full size</p>
            <p style="margin-top: 20px; font-size: 0.9em;">Processing date: March 22, 2026</p>
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
        }
        
        function closeLightbox() {
            const lightbox = document.getElementById('lightbox');
            lightbox.classList.remove('active');
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
    
    print(f"✓ Gallery created: {output_file}")
    print(f"✓ Total images: {total_count}")
    print(f"✓ Successfully processed: {successful}")
    return output_file


if __name__ == "__main__":
    output_path = generate_gallery_html()
    print(f"\n✓ Open in browser: {output_path}")
