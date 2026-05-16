import cv2
import numpy as np
from PIL import Image

def load_image(file_path: str) -> np.ndarray:
    return cv2.imread(file_path)

def save_image(image: np.ndarray, file_path: str):
    cv2.imwrite(file_path, image)

def resize_image(image: np.ndarray, max_size: int = 2000, min_size: int = 1280) -> np.ndarray:
    h, w = image.shape[:2]
    
    # 1. Handle Upscaling for low-res
    if max(h, w) < min_size:
        scale = min_size / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        # Use INTER_CUBIC for better quality when upscaling
        return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)

    # 2. Handle Downscaling for too-large images
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    
    return image

def get_grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def crop_image(image_path: str, x: float, y: float, w: float, h: float, output_path: str):
    """
    Crop an image based on normalized coordinates (0-1280, 0-720) and save to output_path.
    """
    img = cv2.imread(image_path)
    if img is None:
        return False
        
    img_h, img_w = img.shape[:2]
    
    # Map from 1280x720 space back to actual image pixels
    scale_x = img_w / 1280
    scale_y = img_h / 720
    
    ix = max(0, int(x * scale_x))
    iy = max(0, int(y * scale_y))
    iw = int(w * scale_x)
    ih = int(h * scale_y)
    
    # Ensure crop is within bounds
    cropped = img[iy:iy+ih, ix:ix+iw]
    if cropped.size > 0:
        cv2.imwrite(output_path, cropped)
        return True
    return False
