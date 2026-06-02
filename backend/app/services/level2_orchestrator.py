from typing import List, Tuple
from app.schemas.layer import Layer
from app.schemas.pipeline import SkippedElement
from app.services.simple_level2_service import simple_level2_service
from app.core.config import logger

class Level2Orchestrator:
    def __init__(self):
        pass

    async def run_orchestrator(
        self,
        project_id: str,
        image_path: str,
        l1_layers: List[Layer],
        l2_graphics_candidates: List[Layer],
        bg_color: str
    ) -> Tuple[List[Layer], List[SkippedElement]]:
        """
        Coordinates the execution of the Simplified Level 2 Pipeline.
        """
        logger.info(f"Level 2 Orchestrator: Starting Simplified Level 2 pipeline for project {project_id}")
        
        skipped_elements: List[SkippedElement] = []

        try:
            # Execute the new simplified detector
            final_layers = await simple_level2_service.detect_and_compile(
                image_path=image_path,
                project_id=project_id,
                l1_layers=l1_layers
            )
            
            return final_layers, skipped_elements

        except Exception as err:
            logger.error(f"Level 2 Orchestrator: Pipeline execution raised exception: {err}", exc_info=True)
            return l1_layers, skipped_elements

level2_orchestrator = Level2Orchestrator()
