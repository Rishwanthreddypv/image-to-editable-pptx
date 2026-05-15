from app.services.pptx_service import pptx_service
from app.services.document_service import document_service
from sqlalchemy.ext.asyncio import AsyncSession
import io

class ExportService:
    async def export_to_pptx(self, db: AsyncSession, project_id: str) -> io.BytesIO:
        """
        Orchestrate the export of a project to PPTX.
        """
        # 1. Fetch current document state from DB
        doc = await document_service.get_document(db, project_id)
        
        # 2. Convert to PPTX
        # Note: In a real app, 'doc' would be a Pydantic model with layers
        # Here we adapt the dictionary from get_document mock
        from app.schemas.layer import Layer
        layers = [Layer(**l) for l in doc.get("layers", [])]
        bg_color = doc.get("background_color", "#ffffff")
        
        return pptx_service.create_presentation(layers, background_color=bg_color)

export_service = ExportService()
