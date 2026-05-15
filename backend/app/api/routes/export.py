from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.services.export_service import export_service
from app.core.config import logger

router = APIRouter()

@router.get("/{project_id}/pptx")
async def export_pptx(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and download the PPTX version of the project.
    """
    try:
        logger.info(f"Exporting project {project_id} to PPTX")
        pptx_bundle = await export_service.export_to_pptx(db, project_id)
        
        # Fetch status for skipped elements report
        from app.services.document_service import document_service
        import json
        status = await document_service.get_status(project_id)
        skipped_json = json.dumps(status.get("skipped_elements", []))
        fidelity = str(status.get("fidelity_score", 1.0))

        return StreamingResponse(
            pptx_bundle,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename=project_{project_id}.pptx",
                "X-Skipped-Elements": skipped_json,
                "X-Fidelity-Score": fidelity
            }
        )
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate PowerPoint file")
