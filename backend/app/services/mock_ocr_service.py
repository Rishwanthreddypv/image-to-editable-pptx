from app.services.ocr_service import OCRService
from app.schemas.ocr import OCRResult, OCRLine, OCRWord

class MockOCRService(OCRService):
    async def extract_text(self, image_path: str) -> OCRResult:
        # Mock logic: returns standard placeholder lines
        return OCRResult(
            lines=[
                OCRLine(
                    text="Sample Heading",
                    confidence=0.99,
                    x=100, y=100, w=200, h=40,
                    words=[OCRWord(text="Sample", confidence=0.99, x=100, y=100, w=100, h=40)]
                ),
                OCRLine(
                    text="This is a paragraph of text from the image.",
                    confidence=0.95,
                    x=100, y=160, w=400, h=30,
                    words=[]
                )
            ],
            language="en",
            orientation_angle=0.0
        )

mock_ocr_service = MockOCRService()
