from app.services.preprocessing_service import preprocessing_service
from app.services.mock_ocr_service import mock_ocr_service
from app.services.mock_layout_service import mock_layout_service
from app.services.document_builder_service import document_builder_service
from app.services.azure_service import azure_vision_service
from app.services.level2_orchestrator import level2_orchestrator
from app.schemas.pipeline import PipelineResult, SkippedElement
from app.utils.image_utils import draw_debug_containers
from app.schemas.document import Page
from app.core.config import logger
from PIL import Image
import os
DEBUG_LAYOUT=True
# Keep this OFF for diagram-style reconstruction.
# This avoids turning aligned labels into fake tables.
ENABLE_TABLE_RECONSTRUCTION = False

class PipelineService:
    def __init__(self):
        self.ai_service = azure_vision_service
        logger.info("Pipeline initialized with Azure OpenAI Provider")

    async def run_pipeline(self, project_id: str, image_path: str) -> PipelineResult:
        logger.info(f"Starting pipeline for project {project_id}")
        
        processed_path = await preprocessing_service.process(image_path)

        low_res = False
        confidence = "high"
        edge_cases = []
        skipped = []

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

        result = await self.ai_service.analyze_image(processed_path)

        bg_color = "#ffffff"
        if result:
            layers, metadata, skipped_from_ai = result
            bg_color = metadata.get("background_hex", "#ffffff")
            l1_observed = metadata.get("total_elements_observed", len(layers))

            logger.info("Starting Level 2 Pass via Level 2 Orchestrator")
            all_l2_layers, skipped_gfx = await self.ai_service.analyze_graphics(processed_path)

            try:
                layers, level2_skipped = await level2_orchestrator.run_orchestrator(
                    project_id=project_id,
                    image_path=processed_path,
                    l1_layers=layers,
                    l2_graphics_candidates=all_l2_layers,
                    bg_color=bg_color
                )
                logger.info(f"Level 2 Orchestrator completed. Compiled final layout with {len(layers)} layers.")

                for item in level2_skipped:
                    skipped.append(item)
            except Exception as orch_err:
                logger.error(f"Level 2 Orchestrator failed to run end-to-end: {orch_err}", exc_info=True)

            for item in skipped_gfx:
                skipped.append(SkippedElement(
                    type="image",
                    reason=item.get('reason', 'AI skipped graphic'),
                    geometry=item.get('geometry')
                ))

            debug_image_url = None
            if DEBUG_LAYOUT:
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                debug_filename = f"debug_cleaned_hierarchy_{project_id}.png"
                debug_path = os.path.join(project_root, debug_filename)

                logger.info(f"Generating debug hierarchical layout image at root: {debug_path}")
                success = draw_debug_containers(processed_path, layers, debug_path)

                if success:
                    debug_image_url = f"/root/{debug_filename}"
                    logger.info(f"Debug image successfully generated at root: {debug_path}")
                else:
                    logger.error(f"Failed to generate debug image at: {debug_path}")

            gfx_layers = [l for l in all_l2_layers if l.type == "image"]
            total_observed = l1_observed + len(gfx_layers) + len(skipped_gfx)
            successfully_extracted = len(layers)

            fidelity_score = min(1.0, successfully_extracted / total_observed) if total_observed > 0 else 1.0

            for item in skipped_from_ai:
                skipped.append(SkippedElement(
                    type=item.get('type', 'unknown'),
                    reason=item.get('reason', 'AI skipped element'),
                    geometry=item.get('geometry')
                ))

            if fidelity_score < 0.5 and not skipped:
                skipped.append(SkippedElement(
                    type="multiple",
                    reason="Low resolution/Quality caused AI to miss elements",
                    geometry=None
                ))

        else:
            logger.info("Falling back to mock services")
            layout = await mock_layout_service.detect_layout(processed_path)
            ocr = await mock_ocr_service.extract_text(processed_path)
            layers = document_builder_service.build_layers(ocr, layout)
            fidelity_score = 0.5
            confidence = "low"
            debug_image_url = None

        page = Page(
            id="page_1",
            page_number=1,
            layers=self._correct_layout(layers),
            background_color=bg_color
        )

        return PipelineResult(
            project_id=project_id,
            document=page,
            debug_image_url=debug_image_url,
            fidelity_score=fidelity_score,
            skipped_elements=skipped,
            low_resolution_flag=low_res,
            confidence_level=confidence,
            edge_cases_encountered=edge_cases
        )

    def _correct_layout(self, layers):
        """
        For diagram-style pages, do not run table reconstruction.
        Table reconstruction is useful for documents, but it can turn
        aligned diagram labels into fake tables.
        """
        if not layers:
            return layers

        # Skip table reconstruction for pages that already contain diagram structures.
        has_diagram_structures = any(
            l.type in ["container", "connector", "image"] for l in layers
        )
        if has_diagram_structures:
            return sorted(layers, key=lambda l: (l.geometry.y, l.geometry.x))

        reconstructed_layers = self._reconstruct_tables(layers)
        return sorted(reconstructed_layers, key=lambda l: (l.geometry.y, l.geometry.x))

    def _reconstruct_tables(self, layers):
        """
        Keep this only for real document pages.
        """
        text_layers = [
            l for l in layers
            if l.type == "text" and l.content.get('semantic_role') not in ['NODE_LABEL', 'UI_LABEL', 'HEADING']
        ]

        if len(text_layers) < 4:
            return layers

        TOLERANCE = 12
        lines = []
        visited = set()
        sorted_text = sorted(text_layers, key=lambda l: l.geometry.y)

        for i, l1 in enumerate(sorted_text):
            if i in visited:
                continue

            current_line = [l1]
            visited.add(i)

            for j, l2 in enumerate(sorted_text):
                if j in visited:
                    continue
                if abs(l1.geometry.y - l2.geometry.y) < TOLERANCE:
                    current_line.append(l2)
                    visited.add(j)

            lines.append(sorted(current_line, key=lambda l: l.geometry.x))

        tables_to_create = []
        current_table_rows = []

        for line in lines:
            is_table_row = len(line) > 1
            if is_table_row:
                roles = [l.content.get('semantic_role') for l in line]
                if 'NODE_LABEL' in roles:
                    is_table_row = False

                max_gap = 0
                for k in range(1, len(line)):
                    gap = line[k].geometry.x - (line[k-1].geometry.x + line[k-1].geometry.w)
                    max_gap = max(max_gap, gap)

                if max_gap > 400:
                    is_table_row = False

            if is_table_row:
                if current_table_rows and len(line) != len(current_table_rows[0]):
                    if len(current_table_rows) >= 2:
                        tables_to_create.append(list(current_table_rows))
                    current_table_rows = [line]
                else:
                    current_table_rows.append(line)
            else:
                if len(current_table_rows) >= 2:
                    tables_to_create.append(list(current_table_rows))
                current_table_rows = []

        if len(current_table_rows) >= 2:
            tables_to_create.append(current_table_rows)

        if not tables_to_create:
            return layers

        new_layers = list(layers)
        for table_rows in tables_to_create:
            all_text = [l.content.get("text", "") for row in table_rows for l in row]
            avg_len = sum(len(t) for t in all_text) / len(all_text) if all_text else 0

            if avg_len > 100:
                continue

            logger.info(f"Reconstructing table with {len(table_rows)} rows and {len(table_rows[0])} columns")

            cells = []
            min_x = min(l.geometry.x for row in table_rows for l in row)
            min_y = min(l.geometry.y for row in table_rows for l in row)
            max_r = max(l.geometry.x + l.geometry.w for row in table_rows for l in row)
            max_b = max(l.geometry.y + l.geometry.h for row in table_rows for l in row)

            for r_idx, row in enumerate(table_rows):
                for c_idx, layer in enumerate(row):
                    cells.append({
                        "rowIndex": r_idx,
                        "colIndex": c_idx,
                        "content": layer.content.get("text", ""),
                        "semantic_role": "DATA_CELL"
                    })

            from app.schemas.layer import Layer, GeometryBase
            table_layer = Layer(
                id=f"reconstructed_table_{id(table_rows)}",
                type="table",
                geometry=GeometryBase(x=min_x, y=min_y, w=max_r - min_x, h=max_b - min_y),
                content={
                    "cells": cells,
                    "semantic_role": "TABLE",
                    "label": "data_table"
                }
            )

            table_layer_ids = {l.id for row in table_rows for l in row}
            new_layers = [l for l in new_layers if l.id not in table_layer_ids]
            new_layers.append(table_layer)

        return new_layers

pipeline_service = PipelineService()