from typing import List
from pydantic import BaseModel

class LayoutElement(BaseModel):
    type: str # text, table, figure, heading, etc.
    confidence: float
    x: float
    y: float
    w: float
    h: float

class LayoutResult(BaseModel):
    elements: List[LayoutElement]
    image_width: int
    image_height: int
