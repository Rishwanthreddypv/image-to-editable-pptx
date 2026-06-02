# New Level 2 Plan: Simple & Stable Slide-Diagram Reconstruction

This document presents the architecture, data flow, and design specification for the **Redesigned Level 2 (Additive Graphics & Structure) Pipeline**. The goal is to accurately reconstruct flowchart and architecture-style diagrams (containing shape nodes, text labels, connecting arrows, and nested panels) as native, fully editable elements, while enabling easy manual corrections on the frontend canvas before exporting to PowerPoint.

---

## 1. The New Level 2 Approach in Simple Terms

In simple terms, the new Level 2 approach moves away from slow, expensive, and spatially disoriented AI (LMM) recursive calls, and adopts a **stable, geometry-first computer vision (CV) pipeline with semantic anchoring**:

1. **Find the Pieces First**: We use local OpenCV edge detectors and straight line sensors (Hough line transforms) to identify physical boundaries on the canvas (like boxes, rounded cards, vertical/horizontal lines, and small triangular arrowheads).
2. **Clean Up the Clutter**: We immediately delete tiny contour noise, aspect-ratio artifacts, and double lines (concentric strokes representing borders). If two shape boxes heavily overlap, we keep only one.
3. **Glue Text to Shapes (Semantic Anchoring)**: Instead of treating labels and shapes as separate elements, we check if an editable Level 1 text box resides inside a detected shape. If it does, we bind them together. This ensures the shape is preserved *because* of the text, and acts as the textbox's visual background.
4. **Link Shapes with Arrows (Connector Snapping)**: We trace line segments. If a line endpoint lands very close to a shape border, we snap it. If we find a small arrowhead triangle near the line's tip, we combine them into a directed arrow connector.
5. **Group Only When Obvious**: We create group containers (like a larger box enclosing smaller cards) *only* when there is clear, double-checked structural evidence (like visual containment or shared background color). We avoid complex, hypothetical nesting trees that frustrate users.
6. **Put the User in Control**: The frontend canvas displays all shapes, connectors, and text as individual, standard layers. If the pipeline makes a mistake, the user can easily drag, resize, delete, or recolor elements in the editor. The PPTX export service reads the final modified positions, rendering a pixel-perfect, native PowerPoint file.

---

## 2. Redesigned Level 2 Pipeline Stages (In Order)

To reconstruct architecture diagrams cleanly, the pipeline operates in five distinct, modular, and deterministic stages:

```
[ Input Image ]
       │
       ▼
 ┌───────────┐
 │  STAGE 1  │ ──► Detect visual primitives (contours, Hough lines, arrowheads)
 └───────────┘
       │
       ▼
 ┌───────────┐
 │  STAGE 2  │ ──► Clean duplicates, collapse concentric borders, prune noise
 └───────────┘
       │
       ▼
 ┌───────────┐
 │  STAGE 3  │ ──► Semantic Anchoring: Connect L1 text to shape backgrounds
 └───────────┘
       │
       ▼
 ┌───────────┐
 │  STAGE 4  │ ──► Connector Synthesis: Link shapes via lines + arrowheads
 └───────────┘
       │
       ▼
 ┌───────────┐
 │  STAGE 5  │ ──► Compile to standard editable TS layers for Next.js Konva
 └───────────┘
       │
       ▼
[ Widescreen Writable Canvas ] ──► (User Manual Corrections) ──► [ Native PPTX ]
```

### Stage 2.1: Detect Small Visual Pieces (Atomic CV Extraction)
*   **Goal**: Capture raw geometry contours, straight line segments, and arrowhead points.
*   **Mechanism**:
    *   Apply a **Bilateral Filter** to smooth out canvas textures, JPEG artifacts, and gridlines while keeping shape edges sharp.
    *   Run **Canny Edge Detection** and retrieve structural contours using `cv2.findContours` with the `RETR_TREE` hierarchy. This captures shape boundaries (rectangles, rounded rectangles, cylinders, circles) and their physical parenting levels.
    *   Execute the **Probabilistic Hough Line Transform** (`cv2.HoughLinesP`) to extract straight segments representing connecting lines.
    *   Detect small triangular contours (3-to-5 vertices) that reside near line ends to capture **Arrowheads**.

### Stage 2.2: Clean Duplicates & Noise (Structural Deduplication)
*   **Goal**: Eliminate edge-detection noise, double borders, and redundant overlapping boxes.
*   **Mechanism**:
    *   **Micro-Pruning**: Prune shape contours smaller than `15px` in width/height or `225px²` in area unless they wrap a valid text block.
    *   **Double-Border Collapsing**: When contours represent double-stroke borders (concentric outlines), collapse them into a single shape border if their containment ratio is $> 0.98$ and area ratio is $> 0.80$.
    *   **IoU Suppression (Intersection over Union)**: If two distinct shape boxes overlap with an $\text{IoU} > 0.85$, preserve the one with higher visual contrast or larger area, deleting the redundant duplicate.
    *   **Text-Edge Filtering**: Delete shape contours that outline individual text glyphs (often created by Canny edge residue near characters) by checking if the shape wraps an L1 text element with a tight area ratio ($< 1.35$) and low confidence.

### Stage 2.3: Group Obvious Related Pieces (Semantic Anchoring & Proximity)
*   **Goal**: Bind text labels and connecting lines directly to their physical shape nodes.
*   **Mechanism**:
    *   **Semantic Label Anchoring**: If a Level 1 text textbox resides inside a Level 2 shape (containment $> 0.80$), group them. The shape is marked as a visual container card (`container_type = "card"`), and the text is anchored to its center. This prevents shapes enclosing text from being deleted by L1 overlap rules.
    *   **Line-to-Shape Snapping**: If a Hough line endpoint is within `25px` of a shape boundary, snap the line end exactly to the shape's boundary.
    *   **Arrowhead Merging**: If an arrowhead triangle's centroid is within `20px` of a snapped line endpoint, merge them. The line is upgraded to a directed connector (`is_arrow = True`, `direction = "forward"` or `"backward"`).

### Stage 2.4: Create Containers Only When Structure is Clear
*   **Goal**: Synthesize multi-level container panels (like grouped frames, columns, or logical swimlanes) without over-grouping.
*   **Mechanism**:
    *   A bounding box is synthesized as a parent **Container** layer *only* if:
        1. It physically encloses multiple smaller shape nodes and text boxes (containment $> 0.90$).
        2. It represents a clear OpenCV border contour or is explicitly identified as a layout frame.
    *   **Singleton Shield**: Reject empty container shapes or groups enclosing only one child. If a candidate container contains only a single item, collapse the container and promote the child to root level, preventing redundant bounding card clutter.

### Stage 2.5: Return Editable Layers to the Frontend
*   **Goal**: Export all processed elements into standard JSON-compliant layers.
*   **Mechanism**:
    *   Map extracted shapes to `{ id, type: "container", geometry: {x, y, w, h}, content: { container_type: "rectangle" | "rounded_rectangle" } }`.
    *   Map connectors to `{ id, type: "connector", geometry: {x, y, w, h}, content: { style: "solid" | "dashed", is_arrow: true, direction, endpoints } }`.
    *   Preserve text as editable text layers.
    *   Preserve logos or detailed icons as refined transparent PNG crops (`type: "image"`).

---

## 3. Generalizable and Stable Design

To prevent failure modes on diverse diagrams, the new Level 2 architecture enforces these rules:
1.  **Resolution Proportional Scaling**: OpenCV block sizes and Canny limits scale dynamically with the source image resolution (e.g. `block_size = 2 * (min(W, H) / 100) + 1`). This ensures that thin borders in high-res 4K images and thick borders in low-res slide screenshots are captured with identical accuracy.
2.  **No Single-Image Specialization**: Avoid hardcoding pixel-coordinate anchors. All snapping, deduplication, and groupings run on normalized coordinate systems ($1280 \times 720$) using relative ratios.
3.  **Level 1 Isolation**: The Level 1 text/table pipeline remains completely untouched. L1 coordinates serve as static anchor points that pull Level 2 shapes toward them during semantic snapping.

---

## 4. Supporting Manual Corrections in the Frontend

To ensure users can easily fix any automated parsing errors before export, the design decouples canvas state from backend generation:

```
┌────────────────────────────────────────────────────────┐
│                   Next.js Editor UI                    │
├────────────────────────────────────────────────────────┤
│  * Drag & resize shape boxes on Konva Canvas           │
│  * Double-click text layers to edit content / sizing   │
│  * Adjust connecting line paths or delete elements     │
│  * Group/Ungroup panels manually                       │
└───────────────────────────┬────────────────────────────┘
                            │ (JSON state synchronized via PUT)
                            ▼
┌────────────────────────────────────────────────────────┐
│            FastAPI PPTX Export Synthesis               │
├────────────────────────────────────────────────────────┤
│  * Reads final user-modified layer coordinates         │
│  * Maps "container" shapes to native PPTX AutoShapes   │
│  * Maps "connector" arrows to native PPTX Connector lines│
│  * Maps "text" layers to native editable TextFrames    │
└────────────────────────────────────────────────────────┘
```

1.  **Direct Canvas Mapping**:
    *   **Shapes** are rendered in React Konva as standard `Rect` or rounded-border groups. The user can drag, resize, delete, or change border styles/colors in the `PropertyPanel`.
    *   **Connectors** are drawn as simple editable vector lines.
2.  **Slide Export Fidelity**:
    *   When the user clicks "Export PPTX", the client synchronizes the canvas state.
    *   The `pptx_service.py` reads the layers *exactly* as saved by the user. It translates visual cards to native PowerPoint AutoShapes (`MSO_SHAPE.RECTANGLE` or `MSO_SHAPE.ROUNDED_RECTANGLE`) and connectors to native slide line shapes, ensuring the presentation remains fully editable and visually consistent.
