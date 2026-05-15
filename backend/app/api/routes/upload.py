from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.services.storage_service import storage_service
from app.workers.tasks import process_image_task
from app.services.document_service import document_service
from app.core.config import logger
import uuid

router = APIRouter()

@router.post("/")
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image, initialize a project, and trigger background processing.
    """
    project_id = str(uuid.uuid4())
    logger.info(f"Uploading file: {file.filename} for project {project_id}")
    
    file_path = await storage_service.save_upload(file)
    source_image_url = f"/uploads/{file.filename}"
    
    # Initialize status
    await document_service.set_status(project_id, "pending", 0.0, source_image=source_image_url)
    
    # Trigger async pipeline processing
    background_tasks.add_task(process_image_task, project_id, file_path)
    
    return {"project_id": project_id, "filename": file.filename, "status": "processing"}
