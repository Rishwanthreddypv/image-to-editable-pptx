from typing import Dict

def normalize_coordinates(x: float, y: float, w: float, h: float, img_w: int, img_h: int) -> Dict[str, float]:
    return {
        "x": x / img_w,
        "y": y / img_h,
        "w": w / img_w,
        "h": h / img_h
    }

def denormalize_coordinates(nx: float, ny: float, nw: float, nh: float, img_w: int, img_h: int) -> Dict[str, float]:
    return {
        "x": nx * img_w,
        "y": ny * img_h,
        "w": nw * img_w,
        "h": nh * img_h
    }
