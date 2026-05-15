import cv2
import numpy as np
from app.utils.image_utils import resize_image, get_grayscale
from app.core.config import logger

class PreprocessingService:
    async def process(self, image_path: str) -> str:
        """
        Full preprocessing pipeline: deskew, denoise, resize, normalize.
        Returns path to processed image.
        """
        logger.info(f"Preprocessing image: {image_path}")
        img = cv2.imread(image_path)
        
        # 1. Resize/Upscale
        img = resize_image(img)
        
        # 2. Sharpen (Unsharp Masking) to handle blur
        img = self._sharpen(img)
        
        # 3. Denoise
        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        
        # 4. Deskew (Placeholder logic)
        img = self._deskew(img)
        
        # 5. Contrast Normalization
        img = self._normalize_contrast(img)
        
        processed_path = image_path.replace(".", "_processed.")
        cv2.imwrite(processed_path, img)
        return processed_path

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """Apply unsharp masking to enhance edges."""
        gaussian_3 = cv2.GaussianBlur(image, (0, 0), 2.0)
        unsharp_image = cv2.addWeighted(image, 1.5, gaussian_3, -0.5, 0)
        return unsharp_image

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        # Placeholder for deskewing logic
        return image

    def _normalize_contrast(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

preprocessing_service = PreprocessingService()
