from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class GraphNode(BaseModel):
    id: str
    label: str = ""
    bbox: BBox
    type: str = "rectangle"


class GraphConnection(BaseModel):
    source_id: str
    target_id: str
    direction: Literal["forward", "backward", "none"] = "forward"
    style: Literal["solid", "dashed", "dotted"] = "solid"
    arrow: bool = True
    tension: float = 0.0


class DiagramGraph(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    connections: List[GraphConnection] = Field(default_factory=list)