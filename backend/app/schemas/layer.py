from typing import List
from pydantic import BaseModel

class GeometryBase(BaseModel):
    x: float
    y: float
    w: float
    h: float

class LayerBase(BaseModel):
    type: str
    geometry: GeometryBase
    content: dict

class LayerCreate(LayerBase):
    pass

class Layer(LayerBase):
    id: str

    class Config:
        from_attributes = True
