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
            l1_observed = metadata.get("total_elements_observed", len(layers))
            
            # --- LEVEL 2 PASS START ---
            logger.info("Starting Level 2 Pass: Graphics detection")
            gfx_layers, skipped_gfx = await gemini_service.analyze_graphics(processed_path)
            
            # 1. Deduplicate Level 2 graphics among themselves first
            # If two graphics overlap significantly, keep the larger one or merge them
            deduped_gfx = []
            for g1 in gfx_layers:
                is_duplicate = False
                for i, g2 in enumerate(deduped_gfx):
                    area1 = g1.geometry.w * g1.geometry.h
                    area2 = g2.geometry.w * g2.geometry.h
                    
                    dx = min(g1.geometry.x + g1.geometry.w, g2.geometry.x + g2.geometry.w) - max(g1.geometry.x, g2.geometry.x)
                    dy = min(g1.geometry.y + g1.geometry.h, g2.geometry.y + g2.geometry.h) - max(g1.geometry.y, g2.geometry.y)
                    
                    if dx > 0 and dy > 0:
                        intersection = dx * dy
                        # LOWERED THRESHOLD: If more than 20% of the smaller one is inside the larger one, 
                        # it's likely a fragment or duplicate.
                        overlap_ratio = intersection / min(area1, area2)
                        if overlap_ratio > 0.2:
                            is_duplicate = True
                            # Keep the larger one
                            if area1 > area2:
                                deduped_gfx[i] = g1
                            break
                if not is_duplicate:
                    deduped_gfx.append(g1)

            # 2. Merge graphics into layers if they don't conflict with L1 text/tables
            l2_added_count = 0
            for gfx in deduped_gfx:
                is_valid = True
                
                # REJECTION RULE 1: Size Filter
                # If a graphic is massive (e.g. > 50% of the screen area), it's likely 
                # a background fragment or noise. Icons/logos are rarely this large.
                canvas_area = 1280 * 720
                gfx_area = gfx.geometry.w * gfx.geometry.h
                if gfx_area > (canvas_area * 0.5):
                    is_valid = False
                    skipped.append(SkippedElement(
                        type="image",
                        reason=f"Graphic '{gfx.content.get('label')}' is too large ({int(gfx_area/canvas_area*100)}% of canvas). Likely background. Skipping.",
                        geometry=gfx.geometry.dict()
                    ))
                
                if is_valid:
                    for l1_layer in layers:
                        # Calculate bi-directional overlap
                        intersection_area = self._calculate_intersection(gfx.geometry, l1_layer.geometry)
                        if intersection_area <= 0: continue
                        
                        l1_area = l1_layer.geometry.w * l1_layer.geometry.h
                        
                        # REJECTION RULE 2: Anti-Ghosting
                        # If a graphic covers or is covered by a text/table layer, it will cause "doubling".
                        # We reject the graphic if:
                        # a) The text layer is mostly inside the graphic (intersection/l1_area > 0.2)
                        # b) The graphic is mostly inside the text (intersection/gfx_area > 0.2)
                        overlap_with_l1 = intersection_area / l1_area
                        overlap_of_gfx = intersection_area / gfx_area
                        
                        if overlap_with_l1 > 0.2 or overlap_of_gfx > 0.2:
                            is_valid = False
                            skipped.append(SkippedElement(
                                type="image",
                                reason=f"Graphic '{gfx.content.get('label')}' conflicts with {l1_layer.type} layer (Overlap: {int(max(overlap_with_l1, overlap_of_gfx)*100)}%). Skipping to prevent duplication.",
                                geometry=gfx.geometry.dict()
                            ))
                            break
                
                if is_valid:
                    layers.append(gfx)
                    l2_added_count += 1
            
            for item in skipped_gfx:
                skipped.append(SkippedElement(
                    type="image",
                    reason=item.get('reason', 'AI skipped graphic'),
                    geometry=item.get('geometry')
                ))
            # --- LEVEL 2 PASS END ---

            # Fidelity score calculation
            # We want to know how many of the "observed" elements were successfully extracted
            # Gemini L1 observed includes text/tables. 
            # We add L2 detected (including skipped) to get a total estimate
            total_observed = l1_observed + len(gfx_layers) + len(skipped_gfx)
            successfully_extracted = len(layers)
            
            fidelity_score = min(1.0, successfully_extracted / total_observed) if total_observed > 0 else 1.0
            
            # Map skipped elements from AI to our schema
            for item in skipped_from_ai:
                skipped.append(SkippedElement(
                    type=item.get('type', 'unknown'),
                    reason=item.get('reason', 'AI skipped element'),
                    geometry=item.get('geometry')
                ))
            
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

    def _check_overlap(self, geom1, geom2):
        """Simple AABB overlap check."""
        return not (geom1.x + geom1.w <= geom2.x or
                    geom1.x >= geom2.x + geom2.w or
                    geom1.y + geom1.h <= geom2.y or
                    geom1.y >= geom2.y + geom2.h)

    def _calculate_overlap_ratio(self, geom1, geom2):
        """Calculate what percentage of geom1 is covered by geom2."""
        intersection_area = self._calculate_intersection(geom1, geom2)
        geom1_area = geom1.w * geom1.h
        if geom1_area <= 0: return 0
        return intersection_area / geom1_area

    def _calculate_intersection(self, geom1, geom2):
        """Calculate the area of intersection between two geometries."""
        dx = min(geom1.x + geom1.w, geom2.x + geom2.w) - max(geom1.x, geom2.x)
        dy = min(geom1.y + geom1.h, geom2.y + geom2.h) - max(geom1.y, geom2.y)
        
        if dx >= 0 and dy >= 0:
            return dx * dy
        return 0

    def _correct_layout(self, layers):
        """
        Sort layers and ensure no complete overlaps. 
        Nudging is disabled for slide-based layouts to preserve exact graphic positioning.
        """
        if not layers: return layers
        
        # 1. Heuristic: Group text layers into tables if they form a clear grid
        reconstructed_layers = self._reconstruct_tables(layers)
        
        # 2. Sort layers primarily by y, then by x for consistent tab order in PPTX
        sorted_layers = sorted(reconstructed_layers, key=lambda l: (l.geometry.y, l.geometry.x))
        
        # We no longer nudge elements vertically as presentations often have tightly packed
        # or intentionally overlapping elements.
                
        return sorted_layers

    def _reconstruct_tables(self, layers):
        """
        Identify text layers that are aligned in a grid and merge them into a table layer.
        """
        text_layers = [l for l in layers if l.type == "text"]
        if len(text_layers) < 4: return layers 
        
        # 1. Group ALL text elements by Y coordinate to find logical "lines"
        TOLERANCE = 10 
        lines = []
        visited = set()
        
        # Sort by Y first to process in order
        sorted_text = sorted(text_layers, key=lambda l: l.geometry.y)
        
        for i, l1 in enumerate(sorted_text):
            if i in visited: continue
            
            current_line = [l1]
            visited.add(i)
            
            for j, l2 in enumerate(sorted_text):
                if j in visited: continue
                if abs(l1.geometry.y - l2.geometry.y) < TOLERANCE:
                    current_line.append(l2)
                    visited.add(j)
            
            lines.append(sorted(current_line, key=lambda l: l.geometry.x))
        
        # 2. Identify sequences of lines that have multiple elements (potential tables)
        # and ensure they aren't interrupted by single-element lines (paragraphs)
        tables_to_create = []
        current_table_rows = []
        
        for line in lines:
            # A table row must have multiple elements
            # AND the horizontal gap between elements shouldn't be massive (e.g. > 40% of canvas)
            is_table_row = len(line) > 1
            if is_table_row:
                # Check for extreme horizontal gaps which indicate Header + Page Number
                max_gap = 0
                for k in range(1, len(line)):
                    gap = line[k].geometry.x - (line[k-1].geometry.x + line[k-1].geometry.w)
                    max_gap = max(max_gap, gap)
                
                if max_gap > 450: # More than ~35% of 1280px canvas
                    is_table_row = False

            if is_table_row:
                # If column count changes, it might be a new table or just noise
                if current_table_rows and len(line) != len(current_table_rows[0]):
                    if len(current_table_rows) >= 2:
                        tables_to_create.append(list(current_table_rows))
                    current_table_rows = [line]
                else:
                    current_table_rows.append(line)
            else:
                # Interrupting line (paragraph or title)
                if len(current_table_rows) >= 2:
                    tables_to_create.append(list(current_table_rows))
                current_table_rows = []
        
        if len(current_table_rows) >= 2:
            tables_to_create.append(current_table_rows)
            
        if not tables_to_create:
            return layers

        # 3. Process the identified tables
        new_layers = list(layers)
        for table_rows in tables_to_create:
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
                        "content": layer.content.get("text", "")
                    })
            
            from app.schemas.layer import Layer, GeometryBase
            table_layer = Layer(
                id=f"reconstructed_table_{id(table_rows)}",
                type="table",
                geometry=GeometryBase(x=min_x, y=min_y, w=max_r - min_x, h=max_b - min_y),
                content={"cells": cells}
            )
            
            # Remove the original text layers and add the new table layer
            table_layer_ids = {l.id for row in table_rows for l in row}
            new_layers = [l for l in new_layers if l.id not in table_layer_ids]
            new_layers.append(table_layer)
            
        return new_layers


pipeline_service = PipelineService()
