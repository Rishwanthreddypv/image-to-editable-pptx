from typing import List, Optional
from pydantic import BaseModel

class OCRWord(BaseModel):
    text: str
    confidence: float
    x: float
    y: float
    w: float
    h: float

class OCRLine(BaseModel):
    text: str
    confidence: float
    words: List[OCRWord]
    x: float
    y: float
    w: float
    h: float

class OCRResult(BaseModel):
    lines: List[OCRLine]
    language: str
    orientation_angle: float
