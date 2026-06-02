# System Summary: Editable Image to PPTX

This document provides a technical summary of the **Editable Image to PPTX** monorepo, detailing the core system features, active architecture, processing pipeline, Level 1/Level 2 mechanics, and major system weaknesses discovered during our code inspection.

---

## 1. What the Project Does

The **Editable Image to PPTX** system is an end-to-end slide-reconstruction utility. It takes an image of a document or slide (containing text, structured tables, and figures/icons/graphics) and automatically compiles it into a native, fully layered, and editable PowerPoint presentation (`.pptx`). 

Unlike simple PDF-to-image or OCR tools, this application parses elements semantically (identifying headings, body text, tables, card containers, and individual icons), refines icons for transparent backgrounds, and exports them directly into native PowerPoint structures (such as editable text frames, native PowerPoint tables, and cropped alpha-channel image objects) rather than flat images.

---

## 2. Core Architecture

The monorepo operates a decoupled frontend-backend architecture:
- **Frontend (`/frontend`)**: Built in **Next.js 14** (App Router) using **React Konva** for absolute canvas rendering, **Zustand** for visual layer history and page layout options, **Tailwind CSS** for the interface, and dedicated modal grids for table and paragraph modifications.
- **Backend (`/backend`)**: A **FastAPI** application coordinating background tasks using Python's asyncio model, running **OpenCV** for low-level image sharpening/denoising, and **python-pptx** to construct the presentation.
- **Data Definition (`/shared`)**: Shared TypeScript typings and JSON validation schemas to maintain structural consistency between client and server.

---

## 3. How Level 1 and Level 2 Work

The parsing and reconstruction pipeline is divided into two distinct levels to handle semantic types differently:

### 3.1 Level 1: Primary Elements (Text & Tables)
- **Extraction**: Handled by `AzureVisionService.analyze_image()` which prompts Azure OpenAI (GPT-4o) using Chat Completions and JSON Mode to detect all text fragments (headings, paragraphs, node labels) and tables.
- **Table Reconstruction**: If AI fails, or as a post-AI step, `pipeline_service.py` runs `_reconstruct_tables()`. This algorithm groups text elements by Y-coordinate proximity within a tolerance threshold, aligns columns horizontally, and groups them into a single `table` layer if they form a clear grid.
- **PowerPoint Translation**: 
  - Text frames are exported via native textboxes. Coordinate px values are scaled to PowerPoint points using `PT_PER_PX = 0.75` (since a 1280px canvas maps to Inches(13.333) or 960pt). It removes all margins and adds a 5% width safety buffer to prevent standard text wrapping overflows.
  - Tables are generated as native, fully editable table objects populated with text cells.

#### Current Level 1 Strengths
* **Highly Accurate Text Extraction**: The use of advanced LMM vision parses text and semantic roles (like headings or body text) with minimal typos, outperforming traditional OCR engines on low-contrast document images.
* **Flexible Native PowerPoint Outputs**: Reconstructing text as standard slide textboxes and native PowerPoint tables provides immediate editing control, preventing the user from needing to retype raw slide data.
* **Intelligent Borderless Table Recovery**: The `_reconstruct_tables` heuristic groups Y-aligned coordinates to merge text fragments into unified tables, successfully recovering tabular data even when outline borders are completely invisible in the source image.
* **Visual Typography Sync**: Successfully matches color Hex profiles and basic weight/italic styling parameters between web editor views and PPTX slides.
* **Semantic Anchor Role Shielding**: Built-in protection in `_reconstruct_tables` rejects diagram node labels (`NODE_LABEL`, `UI_LABEL`) from table merging, protecting basic flowchart text from accidental grid combination.
* **Overflow Width Safety Buffer**: Incorporates a 5% safety margin on textbox widths during PowerPoint layout compilation to eliminate standard wrapping issues and clipped text.

### 3.2 Level 2: Additive Graphics & Structure
- **Simple Primitive Detector**: The pipeline has been completely simplified to focus on architecture and flowchart diagrams. It uses a single-pass `SimpleLevel2Service` to detect rectangles, rounded boxes, lines, and arrows.
- **Aggressive Deduplication**: Duplicate detections are removed using a high IoU threshold ($> 0.90$), eliminating "ghost shadows" and redundant border layers.
- **Centroid Anchoring**: Level 1 text is mapped to shapes using centroid intersection, ensuring process labels are correctly nested inside their boxes.
- **Vector Connectors**: Fragmented line segments are synthesized into logical connectors. Arrowheads are snapped to the nearest line endpoints to determine direction.
- **Manual Correction**: The pipeline is designed as a "Best Guess" generator. Users can surgicaly add or delete layers in the frontend editor to fix any CV misidentifications before PPTX export.

#### Current Level 2 Weaknesses (Audited)
* **Destructive Overlap Pruning**: Stage 1.75 often deletes process cards if they tightly enclose text labels (area ratio < 1.35), mistaking them for Canny noise.
* **Hough Line Fragmentation**: Long connectors are often broken into 3-4 segments, preventing clean vector arrow reconstruction.
* **O(N^2) Complexity**: Pairwise geometric comparisons in Stage 3 create performance bottlenecks on complex diagrams.
* **Hierarchy Instability**: Redundant wrapper collapsing in Stage 7 can accidentally flatten intended semantic groupings.
* **Gliffy-Style Failures**: Faint grid backgrounds in screenshots trigger thousands of false-positive micro-contours.

---
### 3.3 Redesigned Level 2 Architecture Blueprint (Simple & Stable Flowchart Reconstruction)

The Level 2 pipeline is transitioning to a **Simple Flowchart-First** architecture. This new system prioritizes deterministic geometry and human-in-the-loop correction over complex autonomous hierarchy.

#### New 6-Stage Pipeline
1. **Detect Visual Pieces**: Raw OpenCV extraction of contours and Hough lines.
2. **Clean Duplicates & Noise**: Concentric border collapsing and micro-noise pruning.
3. **Semantic Anchoring & Snap**: Using L1 text as "Gravity Anchors" to snap shapes to labels.
4. **Connector Synthesis**: Snapping line endpoints to container ports and matching arrowheads.
5. **Final Structure Check**: Simple back-to-front Z-index ordering and nesting resolution.
6. **Canvas Layer Mapping**: Exporting native Konva-compatible JSON for the frontend.

#### Integration with Manual Correction
- **Human-in-the-Loop**: The pipeline provides a "Best Guess" layout.
- **Frontend Tools**: Users can delete ghost layers, re-route arrows, and change shape types (e.g., Rectangle to Rounded).
- **PPTX Export**: The `pptx_service.py` uses the **User-Modified JSON** as the final source of truth.

To natively support simple flowchart and block-style architecture diagrams (incorporating boxes, rounded cards, text labels, and connecting arrows), the Level 2 pipeline has been redesigned into a simplified, stable, and deterministic **5-step computer vision and semantic anchoring pipeline**:

1. **Stage 1 — Atomic CV Piece Detection**:
   * Extracts visual primitives (contours, Hough lines, arrowheads) deterministically using bilateral filtering, Canny edges, and probabilistic Hough transforms.
   
2. **Stage 2 — Deduplication & Structural Cleanup**:
   * Prunes micro-contours, aspect ratio noise, and double-stroke concentric borders. Eliminates overlapping redundant shapes using an IoU suppression check (IoU > 0.85).

3. **Stage 3 — Semantic Anchoring (Label & Shape Pairing)**:
   * Maps Level 1 text boundaries directly into enclosing shape geometries. Snaps coordinates, binds the shape as the text box background card, and shields the shape from L1 overlap deletion.

4. **Stage 4 — Connector Synthesis & Arrow Snapping**:
   * Snaps Hough line endpoints to shape nodes within a `25px` proximity radius, and merges close-by arrowhead triangles to synthesize directed, editable flowchart arrows.

5. **Stage 5 — Canvas Layer Mapping**:
   * Compiles elements directly into standard JSON layer objects representing editable shapes, vector connector lines, and alpha-keyed transparent icons for the React Konva web canvas.

The complete engineering plan is documented in [NEW_LEVEL2_PLAN.md](file:///C:/EditableImage/NEW_LEVEL2_PLAN.md). This design completely eliminates $O(N)$ recursive network latency, avoids spatial scale disorientation, and prioritizes user manual correction on the frontend before generating native PowerPoint shapes.

### 3.4 Frontend Editor: Manual Correction Support
- **Manual Layer Editing**: Users can now manually add, move, resize, and delete layers before PPTX export.
- **New Toolbar**: A floating toolbar provides tools for `Select`, `Rectangle`, `Container`, and `Arrow`.
- **Deduplication**: Users can manually remove "ghost layers" or misidentified shapes by selecting them and pressing `Delete`.
- **Integrated History**: Support for `Undo` (Ctrl+Z) and `Redo` (Ctrl+Y) across all manual edits and pipeline-generated adjustments.
- **Export Consistency**: The `TopBar` automatically triggers a `Save` operation before PPTX export, ensuring all manual refinements are included in the final PowerPoint file.

#### Architectural Key Findings & Weaknesses
...

During our in-depth code audit, we identified several critical structural weaknesses and prototype-level patterns:

1. **Transient In-Memory State Bypassing Database**:
   - **Finding**: While SQLAlchemy database engines are set up in `database.py` and SQLite models are defined in `app/models/`, the active backend router completely ignores them!
   - **Weakness**: `DocumentService` maintains all document layers and processing statuses inside local python dictionaries (`self._store` and `self._status`). If the FastAPI server process restarts or crashes, **all uploaded projects, edits, and skipped reports are permanently lost**.
2. **Mismatched and Misplaced Model Files**:
   - **Finding**: In `backend/app/models/`, class names and filenames are completely mismatched:
     - `document_page.py` defines the `SourceImage` class.
     - `document_layer.py` defines the `DocumentPage` class.
     - `edit_history.py` defines the `DocumentLayer` class.
     - There is no model file defining `EditHistory`.
   - **Weakness**: This structural clutter makes database onboarding highly risky and confusing for developers.
3. **Hardcoded Secure Config Paths**:
   - **Finding**: `config.py` uses a hardcoded, platform-specific Windows absolute path to load the environment variables: `env_path = Path(r"C:\secure_configs\.env")`.
   - **Weakness**: This prevents standard environment configurations, breaks cross-platform compatibility (e.g. running in standard Linux Docker setups), and causes immediate crashes if the directory is missing.
4. **Performance Bottleneck in OpenCV Denoising**:
   - **Finding**: `PreprocessingService` uses `cv2.fastNlMeansDenoisingColored` in the synchronous background process.
   - **Weakness**: This function is notoriously CPU-intensive. Processing high-resolution source images will block the single-threaded asyncio background loop, potentially freezing other incoming API requests.
5. **No Paragraph Collision Layout Engine**:
   - **Finding**: As noted in the edge case logs, the editor places paragraphs exactly where the LMM returns them.
   - **Weakness**: Imprecise bounding boxes from LMMs can cause body text and headings to collide or overlap on the slide, requiring significant manual canvas tweaking from the user.

---

## 5. Inspected Files List

Every conclusion in this summary and our project map is based on direct inspection of the following **40 files** inside the repository:

1. [C:/EditableImage/README.md](file:///C:/EditableImage/README.md)
2. [C:/EditableImage/APPROACH.md](file:///C:/EditableImage/APPROACH.md)
3. [C:/EditableImage/EDGE_CASE_LOG.md](file:///C:/EditableImage/EDGE_CASE_LOG.md)
4. [C:/EditableImage/EDGE_CASE_LOG_LEVEL_2.md](file:///C:/EditableImage/EDGE_CASE_LOG_LEVEL_2.md)
5. [C:/EditableImage/SKIPPED_ELEMENTS_REPORT_GUIDE.md](file:///C:/EditableImage/SKIPPED_ELEMENTS_REPORT_GUIDE.md)
6. [C:/EditableImage/backend/app/main.py](file:///C:/EditableImage/backend/app/main.py)
7. [C:/EditableImage/backend/app/api/router.py](file:///C:/EditableImage/backend/app/api/router.py)
8. [C:/EditableImage/backend/app/api/routes/upload.py](file:///C:/EditableImage/backend/app/api/routes/upload.py)
9. [C:/EditableImage/backend/app/api/routes/documents.py](file:///C:/EditableImage/backend/app/api/routes/documents.py)
10. [C:/EditableImage/backend/app/api/routes/export.py](file:///C:/EditableImage/backend/app/api/routes/export.py)
11. [C:/EditableImage/backend/app/workers/tasks.py](file:///C:/EditableImage/backend/app/workers/tasks.py)
12. [C:/EditableImage/backend/app/services/pipeline_service.py](file:///C:/EditableImage/backend/app/services/pipeline_service.py)
13. [C:/EditableImage/backend/app/services/azure_service.py](file:///C:/EditableImage/backend/app/services/azure_service.py)
14. [C:/EditableImage/backend/app/services/layout_hierarchy_service.py](file:///C:/EditableImage/backend/app/services/layout_hierarchy_service.py)
15. [C:/EditableImage/backend/app/services/icon_refinement_service.py](file:///C:/EditableImage/backend/app/services/icon_refinement_service.py)
16. [C:/EditableImage/backend/app/services/pptx_service.py](file:///C:/EditableImage/backend/app/services/pptx_service.py)
17. [C:/EditableImage/backend/app/services/document_service.py](file:///C:/EditableImage/backend/app/services/document_service.py)
18. [C:/EditableImage/backend/app/core/database.py](file:///C:/EditableImage/backend/app/core/database.py)
19. [C:/EditableImage/backend/app/core/config.py](file:///C:/EditableImage/backend/app/core/config.py)
20. [C:/EditableImage/backend/app/services/preprocessing_service.py](file:///C:/EditableImage/backend/app/services/preprocessing_service.py)
21. [C:/EditableImage/backend/app/utils/image_utils.py](file:///C:/EditableImage/backend/app/utils/image_utils.py)
22. [C:/EditableImage/backend/app/utils/coordinate_utils.py](file:///C:/EditableImage/backend/app/utils/coordinate_utils.py)
23. [C:/EditableImage/backend/app/services/document_builder_service.py](file:///C:/EditableImage/backend/app/services/document_builder_service.py)
24. [C:/EditableImage/frontend/app/page.tsx](file:///C:/EditableImage/frontend/app/page.tsx)
25. [C:/EditableImage/frontend/app/document/[id]/page.tsx](file:///C:/EditableImage/frontend/app/document/[id]/page.tsx)
26. [C:/EditableImage/frontend/store/documentStore.ts](file:///C:/EditableImage/frontend/store/documentStore.ts)
27. [C:/EditableImage/frontend/components/editor/EditorCanvas.tsx](file:///C:/EditableImage/frontend/components/editor/EditorCanvas.tsx)
28. [C:/EditableImage/frontend/components/editor/TopBar.tsx](file:///C:/EditableImage/frontend/components/editor/TopBar.tsx)
29. [C:/EditableImage/frontend/lib/api.ts](file:///C:/EditableImage/frontend/lib/api.ts)
30. [C:/EditableImage/frontend/components/editor/PropertyPanel.tsx](file:///C:/EditableImage/frontend/components/editor/PropertyPanel.tsx)
31. [C:/EditableImage/frontend/components/editor/TextLayerEditor.tsx](file:///C:/EditableImage/frontend/components/editor/TextLayerEditor.tsx)
32. [C:/EditableImage/frontend/components/editor/TableLayerEditor.tsx](file:///C:/EditableImage/frontend/components/editor/TableLayerEditor.tsx)
33. [C:/EditableImage/backend/app/schemas/pipeline.py](file:///C:/EditableImage/backend/app/schemas/pipeline.py)
34. [C:/EditableImage/backend/app/schemas/layer.py](file:///C:/EditableImage/backend/app/schemas/layer.py)
35. [C:/EditableImage/shared/types.ts](file:///C:/EditableImage/shared/types.ts)
36. [C:/EditableImage/shared/document.schema.json](file:///C:/EditableImage/shared/document.schema.json)
37. [C:/EditableImage/backend/app/models/project.py](file:///C:/EditableImage/backend/app/models/project.py)
38. [C:/EditableImage/backend/app/models/document_page.py](file:///C:/EditableImage/backend/app/models/document_page.py)
39. [C:/EditableImage/backend/app/models/document_layer.py](file:///C:/EditableImage/backend/app/models/document_layer.py)
40. [C:/EditableImage/backend/app/models/edit_history.py](file:///C:/EditableImage/backend/app/models/edit_history.py)
41. [C:/EditableImage/NEW_LEVEL2_ARCHITECTURE.md](file:///C:/EditableImage/NEW_LEVEL2_ARCHITECTURE.md)
42. [C:/EditableImage/backend/app/services/stage6_hierarchy_service.py](file:///C:/EditableImage/backend/app/services/stage6_hierarchy_service.py)
43. [C:/EditableImage/backend/app/services/stage7_cleanup_service.py](file:///C:/EditableImage/backend/app/services/stage7_cleanup_service.py)
44. [C:/EditableImage/backend/app/services/stage1_5_reconstruction_service.py](file:///C:/EditableImage/backend/app/services/stage1_5_reconstruction_service.py)
45. [C:/EditableImage/backend/app/tests/test_stage1_5_reconstruction.py](file:///C:/EditableImage/backend/app/tests/test_stage1_5_reconstruction.py)
