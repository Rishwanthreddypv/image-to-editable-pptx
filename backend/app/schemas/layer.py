from typing import List, Optional
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
    style: Optional[dict] = {}
    parent_group_id: Optional[str] = None
    group_type: Optional[str] = None
    child_layer_ids: Optional[List[str]] = []

class LayerCreate(LayerBase):
    pass

class Layer(LayerBase):
    id: str

    class Config:
        from_attributes = True
