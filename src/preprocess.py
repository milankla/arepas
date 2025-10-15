import numpy as np
from PIL import Image
import pandas as pd
from loguru import logger
import base64
from io import BytesIO

def prepare_images_for_openai(image_paths, max_size=(1024, 1024)):
    """
    Prepare images for OpenAI Vision API by ensuring they meet size requirements.
    
    Args:
        image_paths: List of image file paths
        max_size: Maximum size (width, height) for images
        
    Returns:
        List of image paths (resized if necessary) ready for OpenAI API
    """
    logger.info(f"Preparing {len(image_paths)} images for OpenAI Vision API")
    prepared_paths = []
    
    for i, img_path in enumerate(image_paths):
        if i % 100 == 0:  # Log progress every 100 images
            logger.debug(f"Processing image {i+1}/{len(image_paths)}")
        
        try:
            with Image.open(img_path) as img:
                # Check if image needs resizing
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    # Save resized image with modified name
                    base_path = img_path.rsplit('.', 1)[0]
                    ext = img_path.rsplit('.', 1)[1] if '.' in img_path else 'jpg'
                    resized_path = f"{base_path}_resized.{ext}"
                    img.save(resized_path)
                    prepared_paths.append(resized_path)
                else:
                    prepared_paths.append(img_path)
        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
            continue
    
    logger.info(f"Successfully prepared {len(prepared_paths)} images for OpenAI Vision API")
    return prepared_paths

def encode_image_to_base64(image_path):
    """
    Encode an image file to base64 string for OpenAI API.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image {image_path} to base64: {e}")
        return None

def preprocess_attributes(df):
    """
    Preprocess attribute DataFrame for training.
    
    Args:
        df: pandas DataFrame with building attributes
        
    Returns:
        Processed DataFrame
    """
    logger.info(f"Preprocessing attributes DataFrame with {len(df)} rows and {len(df.columns)} columns")
    
    # Log missing values
    missing_counts = df.isnull().sum()
    total_missing = missing_counts.sum()
    if total_missing > 0:
        logger.warning(f"Found {total_missing} missing values across {(missing_counts > 0).sum()} columns")
        for col, count in missing_counts[missing_counts > 0].items():
            logger.debug(f"Column '{col}': {count} missing values")
    
    # Placeholder: implement attribute normalization/encoding as needed
    result = df.fillna(0)
    logger.info(f"Successfully preprocessed attributes, filled {total_missing} missing values with 0")
    return result
