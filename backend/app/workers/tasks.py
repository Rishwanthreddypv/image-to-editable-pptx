from app.services.pipeline_service import pipeline_service
from app.services.document_service import document_service
from app.core.config import logger
import asyncio

async def process_image_task(project_id: str, image_path: str):
    """
    Background task to run the full image processing pipeline.
    Updates the document status along the way.
    """
    try:
        logger.info(f"Background task started for {project_id}")
        await document_service.set_status(project_id, "processing", 10.0)
        
        # Simulate processing time for UI feedback
        await asyncio.sleep(1)
        await document_service.set_status(project_id, "processing", 50.0)
        
        result = await pipeline_service.run_pipeline(project_id, image_path)
        
        # Save the structured document model
        await document_service.save_document(project_id, result.document, debug_image_url=result.debug_image_url)
        
        await asyncio.sleep(0.5)
        await document_service.set_status(
            project_id, 
            "completed", 
            100.0,
            fidelity_score=result.fidelity_score,
            low_resolution_flag=result.low_resolution_flag,
            confidence_level=result.confidence_level,
            edge_cases_encountered=result.edge_cases_encountered,
            skipped_elements=[s.model_dump() for s in result.skipped_elements],
            debug_image_url=result.debug_image_url
        )
        logger.info(f"Background task completed for {project_id}")
    except Exception as e:
        logger.error(f"Pipeline failed for {project_id}: {str(e)}")
        await document_service.set_status(project_id, "failed", 0.0)
