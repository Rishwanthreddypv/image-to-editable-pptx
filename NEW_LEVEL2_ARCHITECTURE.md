# New Level 2 Architecture: Simple Flowchart-First Pipeline

This document outlines the redesigned Level 2 pipeline for **Editable Image to PPTX**. The architecture shifts from a "perfect hierarchy" goal to a "stable, editable structure" goal, optimized for simple architecture diagrams and flowcharts.

---

## 1. Core Principles
- **L1 Preservation**: Level 1 (Text/Tables) is the immutable foundation.
- **Gravity Anchors**: Text anchors drive shape detection; we "seek" shapes around text.
- **Deterministic Geometry**: Prioritize OpenCV-based shapes over fuzzy LMM guesses.
- **Frontend-First**: Design for human correction. If the pipeline is unsure, it preserves "Unknown" objects for the user to refine on the canvas.
- **No Recursion**: Eliminate $O(N)$ AI calls. Use single-pass extraction + geometric synthesis.

---

## 2. Pipeline Stages

### Stage 1: Detect Visual Pieces
*   **Purpose**: Extract raw geometric primitives from the image.
*   **Inputs**: Source Image (BGR), Grayscale mask.
*   **Outputs**: List of `RawPrimitive` (bbox, type: [box, line, blob], contour_data).
*   **Algorithms**: 
    - `cv2.Canny` + `cv2.findContours` (RETR_TREE) for closed shapes.
    - `cv2.HoughLinesP` for shaft segments.
    - `cv2.approxPolyDP` to classify rectangles vs. circles.
*   **Debug Artifacts**: `debug_l2_s1_raw_contours.png`.

### Stage 2: Clean Duplicates & Noise
*   **Purpose**: Collapse redundant edge detections and prune micro-noise.
*   **Inputs**: List of `RawPrimitive`.
*   **Outputs**: Deduplicated `CleanPrimitive` list.
*   **Algorithms**:
    - **Concentric Collapse**: If two boxes share IoU > 0.85 and enclosure > 0.95, keep the outer one.
    - **Micro Pruning**: Remove anything with area < 100px unless it has high circularity (icons).
    - **Collinear Merging**: Merge fragmented Hough lines sharing the same vector and < 15px gap.
*   **Debug Artifacts**: `debug_l2_s2_clean_primitives.json`.

### Stage 3: Semantic Anchoring & Snap (Gravity)
*   **Purpose**: Link visual shapes to semantic L1 text labels.
*   **Inputs**: `CleanPrimitive` list + `L1_Layers` (Text).
*   **Outputs**: `AnchoredLayer` list (Shape + Text ID reference).
*   **Algorithms**:
    - **Centroid Enclosure**: If a shape encloses a text centroid, it becomes a "Container".
    - **Padding Snap**: Snap the box edges to the text bounding box + 10px padding if the box is "tight".
    - **Confidence Boost**: Shapes containing text are upgraded to `confidence: 0.95`.
*   **Failure Cases**: Text outside its intended box (drift) or overlapping boxes.
*   **Debug Artifacts**: `debug_l2_s3_gravity_anchors.png`.

### Stage 4: Connector Synthesis
*   **Purpose**: Reconstruct logical arrows from fragmented lines and arrowheads.
*   **Inputs**: Remaining `CleanPrimitive` (lines/blobs) + `AnchoredLayer` (containers).
*   **Outputs**: `ConnectorLayer` list (source_id, target_id, path_type).
*   **Algorithms**:
    - **Port Snapping**: Check line endpoints against container boundaries (dist < 20px).
    - **Arrowhead Match**: Scan for small triangles/V-shapes at endpoints.
    - **Orthogonal Routing**: Force lines to be H/V if they are within 5 degrees of axis.
*   **Debug Artifacts**: `debug_l2_s4_connectors.png`.

### Stage 5: Final Structure Check
*   **Purpose**: Resolve Z-index and simple nesting.
*   **Inputs**: All layers.
*   **Outputs**: Validated `DocumentTree`.
*   **Algorithms**:
    - **Area Sorting**: Sort by Area descending to establish Z-index (Back-to-Front).
    - **Enclosure Hierarchy**: If Box A contains Box B, Box B is a child of A.
*   **Debug Artifacts**: `debug_l2_s5_hierarchy_map.json`.

### Stage 6: Canvas Layer Mapping
*   **Purpose**: Map internal types to React Konva / PPTX compatible JSON.
*   **Inputs**: `DocumentTree`.
*   **Outputs**: `final_document.json`.
*   **Mapping**:
    - `Rectangle` -> `Shape(rect)`
    - `Rounded_Rectangle` -> `Shape(rect, cornerRadius)`
    - `Arrow` -> `Connector(points, head)`
    - `Panel` -> `Group(children)`

---

## 3. Support for Manual Correction

### 3.1 The Frontend Workflow
The pipeline is designed to be **imperfect but helpful**. 
1. **Status**: "Pipeline Finished with 85% Confidence".
2. **Action**: User opens the editor.
3. **De-cluttering**: 
    - Duplicate/Ghost layers can be selected and deleted with `Delete` or `Backspace`.
    - "Select All" + "Filter by Type" allows batch deletion of noise (e.g., small blobs).
4. **Correction**:
    - **Add Arrow**: User clicks "Connector" tool, drags from Box A to Box B. The system saves this as a native connector.
    - **Convert Shape**: User right-clicks a `Rectangle` and selects "Convert to Rounded Rectangle".
    - **Group**: User drags a box over multiple items and clicks "Group" to create a custom container.

### 3.2 Backend Integration
- The frontend sends the **modified** JSON back to the backend for PPTX export.
- The `pptx_service.py` treats the modified JSON as the "Source of Truth," ignoring the original pipeline output.

---

## 4. Stability Features
- **Deterministic Snap**: No fuzzy coordinate guesses. Boxes snap to L1 text or LMM candidates only if IoU is high.
- **Port Anchors**: Arrows are defined by their **Relationship** (Start: Container_A, End: Container_B) rather than just static coordinates. This allows the user to move a box and have the arrow follow it.
