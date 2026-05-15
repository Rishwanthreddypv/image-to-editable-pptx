from pydantic import BaseModel
from typing import Optional, List, Any
from app.schemas.document import Page

class SkippedElement(BaseModel):
    type: str
    reason: str
    geometry: Optional[dict] = None

class PipelineStatus(BaseModel):
    project_id: str
    status: str # processing, completed, failed
    progress: float
    error_message: Optional[str] = None

class PipelineResult(BaseModel):
    project_id: str
    document: Page
    fidelity_score: float = 1.0
    skipped_elements: List[SkippedElement] = []
    low_resolution_flag: bool = False
    confidence_level: str = "high" # high, medium, low
    edge_cases_encountered: List[str] = []
