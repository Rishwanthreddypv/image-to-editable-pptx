from abc import ABC, abstractmethod
from app.schemas.ocr import OCRResult

class OCRService(ABC):
    @abstractmethod
    async def extract_text(self, image_path: str) -> OCRResult:
        pass
