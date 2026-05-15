from typing import List, Optional
from pydantic import BaseModel
from app.schemas.layer import Layer

class PageBase(BaseModel):
    page_number: int

class Page(PageBase):
    id: str
    layers: List[Layer]
    background_color: str = "#ffffff"

    class Config:
        from_attributes = True

class DocumentUpdate(BaseModel):
    layers: List[Layer]
    background_color: Optional[str] = None
