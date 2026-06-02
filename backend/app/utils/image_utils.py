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

def draw_debug_containers(image_path: str, layers: list, output_path: str):
    """
    Draw colored bounding boxes and labels for ALL layers onto a copy of the image.
    Visualizes hierarchy levels and SEMANTIC ROLES.
    """
    from app.core.config import logger
    
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Debug Rendering: Could not read image at {image_path}")
        return False

    img_h, img_w = img.shape[:2]
    scale_x = img_w / 1280
    scale_y = img_h / 720

    # Semantic Role Palette (BGR)
    ROLE_COLORS = {
        "STRUCTURAL_CONTAINER": (0, 0, 255),    # Red
        "CONTENT_NODE": (255, 0, 0),            # Blue
        "TABLE": (0, 165, 255),                 # Orange
        "UI_CHROME": (128, 128, 128),           # Gray
        "CONNECTOR": (0, 255, 255),             # Yellow
        "DECORATIVE": (200, 200, 200),          # Light Gray
        "TEXT_GROUP": (0, 255, 0),              # Green
        "ICON_GROUP": (255, 0, 255),            # Magenta
        "HEADING": (0, 0, 128),                 # Maroon
        "PARAGRAPH": (0, 128, 0),               # Dark Green
        "DATA_CELL": (128, 0, 0),               # Navy
        "NODE_LABEL": (128, 0, 128)             # Purple
    }

    # 1. build a map to calculate hierarchy levels for containers
    id_to_layer = {l.id: l for l in layers}
    
    # 2. Draw Child Links
    for layer in layers:
        if layer.parent_group_id:
            parent = id_to_layer.get(layer.parent_group_id)
            if parent:
                px = int((parent.geometry.x + parent.geometry.w/2) * scale_x)
                py = int((parent.geometry.y + parent.geometry.h/2) * scale_y)
                cx = int((layer.geometry.x + layer.geometry.w/2) * scale_x)
                cy = int((layer.geometry.y + layer.geometry.h/2) * scale_y)
                cv2.line(img, (px, py), (cx, cy), (180, 180, 180), 1)

    # 3. Draw Bounding Boxes
    for layer in layers:
        role = layer.content.get('semantic_role', 'STRUCTURAL_CONTAINER' if layer.type == 'container' else 'CONTENT_NODE')
        color = ROLE_COLORS.get(role, (0, 255, 0))
        
        thickness = 2
        if role == "STRUCTURAL_CONTAINER": thickness = 3
        if role == "UI_CHROME": thickness = 1

        try:
            x1 = int(layer.geometry.x * scale_x)
            y1 = int(layer.geometry.y * scale_y)
            w = int(layer.geometry.w * scale_x)
            h = int(layer.geometry.h * scale_y)
            x2, y2 = x1 + w, y1 + h

            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

            # Label
            label_text = f"{role[:4]}: {layer.content.get('label', '') or layer.id[:4]}"
            conf = layer.content.get('confidence', 1.0)
            if conf < 1.0: label_text += f" ({int(conf*100)}%)"
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.35
            txt_thickness = 1
            
            (label_w, label_h), _ = cv2.getTextSize(label_text, font, font_scale, txt_thickness)
            label_y = y1 - 2
            if label_y < 12: label_y = y1 + label_h + 2
                
            cv2.rectangle(img, (x1, label_y - label_h - 2), (x1 + label_w + 2, label_y + 2), color, -1)
            cv2.putText(img, label_text, (x1 + 1, label_y), font, font_scale, (255, 255, 255), txt_thickness)
        except Exception as e:
            logger.error(f"Error drawing debug box for layer {layer.id}: {e}")

    success = cv2.imwrite(output_path, img)
    return success

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
