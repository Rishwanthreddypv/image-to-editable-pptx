from abc import ABC, abstractmethod
from app.schemas.layout import LayoutResult

class LayoutService(ABC):
    @abstractmethod
    async def detect_layout(self, image_path: str) -> LayoutResult:
        pass
