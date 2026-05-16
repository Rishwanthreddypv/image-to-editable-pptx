from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.services.document_service import document_service
from app.schemas.document import DocumentUpdate

router = APIRouter()

@router.get("/{project_id}/status")
async def get_document_status(project_id: str):
    """
    Retrieve the processing status of a document.
    """
    return await document_service.get_status(project_id)

@router.get("/{project_id}")
async def get_document(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the current document model for a project.
    """
    doc = await document_service.get_document(db, project_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Return document id at root level for frontend schema matching
    return {
        "id": project_id, 
        "layers": doc.get("layers", []),
        "sourceImage": doc.get("sourceImage"),
        "background_color": doc.get("background_color", "#ffffff")
    }

@router.put("/{project_id}")
async def update_document(
    project_id: str,
    doc_update: DocumentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update layers in the document model.
    """
    return await document_service.update_document(db, project_id, doc_update)
