from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.document import DocumentUpdate

class DocumentService:
    def __init__(self):
        # In-memory stores for this prototype phase
        # In a real system, these would be saved to PostgreSQL / NoSQL
        self._store = {}
        self._status = {}

    async def get_document(self, db: AsyncSession, project_id: str):
        return self._store.get(project_id, None)

    async def update_document(self, db: AsyncSession, project_id: str, doc_update: DocumentUpdate):
        if project_id in self._store:
            self._store[project_id]["layers"] = [l.model_dump() for l in doc_update.layers]
            if doc_update.background_color:
                self._store[project_id]["background_color"] = doc_update.background_color
        return {"status": "updated", "project_id": project_id}

    async def get_status(self, project_id: str):
        return self._status.get(project_id, {
            "status": "not_found", 
            "progress": 0.0, 
            "sourceImage": None,
            "fidelity_score": 1.0,
            "low_resolution_flag": False,
            "confidence_level": "high",
            "edge_cases_encountered": [],
            "skipped_elements": []
        })

    async def set_status(self, project_id: str, status: str, progress: float, **kwargs):
        if project_id not in self._status:
            self._status[project_id] = {}
        self._status[project_id].update({"status": status, "progress": progress})
        self._status[project_id].update(kwargs)

    async def save_document(self, project_id: str, document_page):
        # Model dump ensures it serializes well to dict
        data = document_page.model_dump()
        # Ensure we keep the source image reference if it exists
        if project_id in self._status:
            data["sourceImage"] = self._status[project_id].get("sourceImage")
        self._store[project_id] = data

document_service = DocumentService()
