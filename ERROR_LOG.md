# Error & Vulnerability Log: Editable Image to PPTX

This document lists architectural bugs, potential runtime failures, performance bottlenecks, and design structural flaws discovered during our static inspection of the **Editable Image to PPTX** monorepo.

---

## 1. Resolved Failure Modes (Archive)

> [!NOTE]
> This section lists critical failures that were successfully mitigated through architecture redesigns and implementation updates.

### 1.1 Level 2 Pipeline Logic
- **Destructive Overlap Pruning**: 
  - **Issue**: Standard diagram nodes were deleted if they enclosed text labels due to a 30% area overlap threshold.
  - **Resolved**: Pivot to **Centroid Gravity Anchoring**. Text layers are now non-destructively bound to enclosing shapes, boosting shape confidence instead of triggering deletion.
- **Concentric Shadow Artifacts**: 
  - **Issue**: Thick borders were detected as multiple nested boxes.
  - **Resolved**: Aggressive **IoU Suppression (> 0.90)** and concentric border collapsing logic.
- **Hough Line Fragmentation**:
  - **Issue**: Continuous arrows were broken into multiple segments.
  - **Resolved**: Single-pass **Connector Synthesis** that snaps fragmented line endpoints to container ports and binds arrowheads via proximity.

---

## 2. Current Architectural Weaknesses

### 2.1 Level 2: Simplified Diagram Primitive Detector

The consolidated `SimpleLevel2Service` is highly stable for flowcharts but introduces the following risks:

#### 2.1.1 Nested Complexity Flattening
* **Location**: `backend/app/services/simple_level2_service.py`
* **Weakness**: By ignoring deep contour hierarchies, the detector may fail to properly nest children in complex multi-panel diagrams (e.g. 4+ levels of boxes). It defaults to a flatter Z-index structure.
* **Risk**: High for complex enterprise architecture diagrams. Low for simple flowcharts.

#### 2.1.2 Style & Color Detection Gap
* **Location**: `backend/app/services/simple_level2_service.py`
* **Weakness**: The current simplified pipeline does not analyze the pixel colors of detected shapes. All generated shapes default to a semi-transparent white fill and black stroke.
* **Risk**: Users must manually set colors in the editor if the source diagram has color-coded nodes (e.g. "Green for Success", "Red for Error").

#### 2.1.3 Multi-Segment (Elbow) Connector Fragmentation
* **Location**: `backend/app/services/simple_level2_service.py`
* **Weakness**: Horizontal/Vertical elbow connectors are still detected as multiple individual straight `connector` objects rather than a single polyline path.
* **Risk**: Moving one part of an elbow arrow in the editor requires moving 2-3 segments independently.

---

## 3. Frontend Manual Correction Weaknesses

### 3.1 Static Layer Creation
* **Issue**: New layers (Rectangle, Container, Arrow) are added at fixed center coordinates (e.g., 150, 150).
* **Consequence**: Users must move every manually added object to its intended location; a "drag-to-create" UX is missing.

### 3.2 Missing Z-Index UI
* **Issue**: While the pipeline sorts layers (Text > Connectors > Shapes), there is no frontend button for "Send to Back" or "Bring to Front."
* **Consequence**: Manually added shapes might accidentally obscure existing text if they are added later in the session.

---

## 4. Performance Bottlenecks

### 4.1 OpenCV Adaptive Thresholding
* **Location**: `SimpleLevel2Service._detect_raw_primitives`
* **Issue**: Running adaptive thresholding on ultra-high-resolution images (4K+) can take 200-500ms on a single CPU core.
* **Risk**: Large batches of high-res images could block the async worker loop.

---

## 5. Metadata & Data Integrity

### 5.1 Transient In-Memory State
* **Issue**: `DocumentService` uses a Python dictionary for state storage.
* **Consequence**: Server restarts clear all user edits and uploaded project data. (Note: Database persistence is configured in models but not yet wired to the service).
