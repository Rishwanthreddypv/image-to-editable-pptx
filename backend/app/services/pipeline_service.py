from app.services.preprocessing_service import preprocessing_service
from app.services.mock_ocr_service import mock_ocr_service
from app.services.mock_layout_service import mock_layout_service
from app.services.document_builder_service import document_builder_service
from app.services.gemini_service import gemini_service
from app.schemas.pipeline import PipelineResult, SkippedElement
from app.schemas.document import Page
from app.core.config import logger
from PIL import Image
import os

class PipelineService:
    async def run_pipeline(self, project_id: str, image_path: str) -> PipelineResult:
        logger.info(f"Starting pipeline for project {project_id}")
        
        # 1. Preprocessing
        processed_path = await preprocessing_service.process(image_path)
        
        # Initial metadata/edge case tracking
        low_res = False
        confidence = "high"
        edge_cases = []
        skipped = []
        
        # Check resolution
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                if w < 1280 or h < 720:
                    low_res = True
                    if w < 640 or h < 360:
                        confidence = "low"
                    else:
                        confidence = "medium"
                    edge_cases.append(f"Low resolution input detected ({w}x{h})")
                    logger.warning(f"Low resolution detected: {w}x{h}")
        except Exception as e:
            logger.error(f"Failed to check resolution: {e}")

        # 2. Try Gemini Vision first
        result = await gemini_service.analyze_image(processed_path)
        
        bg_color = "#ffffff"
        if result:
            layers, metadata, skipped_from_ai = result
            bg_color = metadata.get("background_hex", "#ffffff")
            observed_count = metadata.get("total_elements_observed", len(layers))
            
            # Map skipped elements from AI to our schema
            for item in skipped_from_ai:
                skipped.append(SkippedElement(
                    type=item.get('type', 'unknown'),
                    reason=item.get('reason', 'AI skipped element'),
                    geometry=item.get('geometry')
                ))

            if bg_color.lower() in ["#ffffff", "#000000", "white", "black"]:
                edge_cases.append("Slide with no detectable background pattern")
            
            # Fidelity score calculation
            # score = successfully_parsed / total_observed
            successfully_parsed = len(layers)
            fidelity_score = min(1.0, successfully_parsed / observed_count) if observed_count > 0 else 1.0
            
            # If fidelity is low but skipped is empty, add a placeholder
            if fidelity_score < 0.5 and not skipped:
                skipped.append(SkippedElement(
                    type="multiple",
                    reason="Low resolution/Quality caused AI to miss elements",
                    geometry=None
                ))
            
        else:
            logger.info("Falling back to mock services")
            # 3. Layout Detection (Async/Mock)
            layout = await mock_layout_service.detect_layout(processed_path)
            
            # 4. OCR (Async/Mock)
            ocr = await mock_ocr_service.extract_text(processed_path)
            
            # 5. Document Building
            layers = document_builder_service.build_layers(ocr, layout)
            fidelity_score = 0.5 # Mock score
            confidence = "low"
        
        page = Page(
            id="page_1",
            page_number=1,
            layers=self._correct_layout(layers),
            background_color=bg_color
        )
        
        return PipelineResult(
            project_id=project_id,
            document=page,
            fidelity_score=fidelity_score,
            skipped_elements=skipped,
            low_resolution_flag=low_res,
            confidence_level=confidence,
            edge_cases_encountered=edge_cases
        )

    def _correct_layout(self, layers):
        """
        Sort layers by vertical position and ensure no overlaps.
        """
        if not layers: return layers
        
        # Sort layers primarily by y, then by x
        sorted_layers = sorted(layers, key=lambda l: (l.geometry.y, l.geometry.x))
        
        # Minimum vertical gap between elements (increased for better PPTX separation)
        min_gap = 25
        
        for i in range(1, len(sorted_layers)):
            prev = sorted_layers[i-1]
            curr = sorted_layers[i]
            
            # Check for vertical overlap or proximity
            prev_bottom = prev.geometry.y + prev.geometry.h
            
            # Horizontal overlap check: if elements are in the same vertical column
            h_overlap = not (curr.geometry.x >= prev.geometry.x + prev.geometry.w or
                             curr.geometry.x + curr.geometry.w <= prev.geometry.x)
            
            if h_overlap and curr.geometry.y < prev_bottom + min_gap:
                logger.info(f"Nudging layer {curr.id} (y: {curr.geometry.y}) to {prev_bottom + min_gap} to avoid overlap")
                curr.geometry.y = prev_bottom + min_gap
                
        return sorted_layers

pipeline_service = PipelineService()
