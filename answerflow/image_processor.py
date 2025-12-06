"""
Image processing utilities for AnswerFlow.
"""

import base64
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io

from answerflow.logger import logger


class ImageProcessor:
    """Handles image processing operations."""
    
    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """
        Encode an image file to base64 string.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Base64 encoded string of the image
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                logger.debug(f"Encoded image: {image_path}")
                return encoded
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            raise
    
    @staticmethod
    def get_image_info(image_path: str) -> dict:
        """
        Get information about an image.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Dictionary containing image information
        """
        try:
            with Image.open(image_path) as img:
                info = {
                    "path": image_path,
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                }
                logger.debug(f"Image info for {image_path}: {info}")
                return info
        except Exception as e:
            logger.error(f"Error getting image info for {image_path}: {e}")
            raise
    
    @staticmethod
    def resize_image(
        image_path: str,
        max_width: int = 1920,
        max_height: int = 1080,
        output_path: Optional[str] = None
    ) -> str:
        """
        Resize an image if it exceeds the maximum dimensions.
        
        Args:
            image_path: Path to the image file
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            output_path: Path to save the resized image (optional)
        
        Returns:
            Path to the resized image
        """
        try:
            with Image.open(image_path) as img:
                # Calculate new dimensions
                width, height = img.size
                if width <= max_width and height <= max_height:
                    logger.debug(f"Image {image_path} does not need resizing")
                    return image_path
                
                # Calculate resize ratio
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                if output_path is None:
                    output_path = str(Path(image_path).with_suffix('.resized' + Path(image_path).suffix))
                
                resized_img.save(output_path)
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Error resizing image {image_path}: {e}")
            raise
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """
        Validate if a file is a valid image.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            True if the file is a valid image, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                img.verify()
                logger.debug(f"Image {image_path} is valid")
                return True
        except Exception as e:
            logger.error(f"Invalid image {image_path}: {e}")
            return False
