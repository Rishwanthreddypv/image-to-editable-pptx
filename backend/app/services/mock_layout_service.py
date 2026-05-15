from app.services.layout_service import LayoutService
from app.schemas.layout import LayoutResult, LayoutElement

class MockLayoutService(LayoutService):
    async def detect_layout(self, image_path: str) -> LayoutResult:
        return LayoutResult(
            elements=[
                LayoutElement(type="heading", confidence=0.9, x=100, y=50, w=300, h=40),
                LayoutElement(type="table", confidence=0.95, x=100, y=120, w=1000, h=300),
                LayoutElement(type="text", confidence=0.9, x=100, y=450, w=800, h=100),
                LayoutElement(type="image", confidence=0.85, x=100, y=570, w=300, h=100)
            ],
            image_width=1280,
            image_height=720
        )

mock_layout_service = MockLayoutService()
