# Level 2 Implementation Audit: Hybrid Modular Pipeline

This document provides a detailed technical audit of the current Level 2 (Graphics & Containers) implementation. It traces the logic, identifies strengths and systemic failures, and compares the existing "Modular Hybrid" strategy against the desired "Simple Flowchart-First" redesign.

---

## 1. Trace of the Exact Level 2 Flow

The current Level 2 pipeline is an advanced, 7-stage modular system orchestrated by `Level2Orchestrator`. It attempts to bridge deterministic Computer Vision (OpenCV) with semantic AI insights (GPT-4o).

### Stage 1: Atomic Extraction (`stage1_extraction_service.py`)
- **Contour Detection**: Uses `cv2.findContours` (RETR_EXTERNAL) with adaptive thresholding to find closed geometric shapes (rectangles, circles, cylinders).
- **Connector Detection**: Uses `cv2.HoughLinesP` to detect straight line segments (shafts).
- **AI Snapping**: Cross-references OpenCV shapes with LMM-detected graphic candidates. If IoU > 0.5, it "snaps" the LMM candidate to the pixel-perfect OpenCV boundary.
- **Text Gravity**: Boosts confidence of shapes enclosing L1 text layers.

### Stage 1.5: Shape & Connector Reconstruction (`stage1_5_reconstruction_service.py`)
- **Hierarchy Analysis**: Uses `RETR_TREE` to identify nested contours (parent/child relationships).
- **Classification**: Distinguishes between `border`, `panel`, `rectangle`, `rounded_rectangle`, `circle`, and `capsule` using solidity, extent, and circularity metrics.
- **Connector Synthesis**: 
  - Groups short collinear line segments into `dashed` connectors.
  - Detects triangular arrowheads and snaps them to shaft endpoints (radius < 20px) to determine `direction`.

### Stage 1.75: Consolidation & Deduplication (`stage1_75_consolidation_service.py`)
- **Pruning**: Removes micro-contours ($< 225\text{px}^2$) and ultra-thin Canny artifacts.
- **Text-Edge Pruning**: Specific logic to remove Canny outlines that tightly wrap ($< 1.35$ area ratio) exactly one text layer.
- **IoU Suppression**: Merges near-identical boxes (IoU > 0.85).
- **Concentric Collapsing**: Collapses double-stroke outlines (containment > 0.98, area ratio > 0.80) into a single structural layer.

### Stage 2: Content vs. Noise Separation (`stage2_separation_service.py`)
- **Position Priors**: Biases elements sitting in the top (toolbar), left/right (sidebar), or center (diagram) zones.
- **Repetition Patterns**: Detects aligned, identical-sized small buttons/palette items.
- **Semantic Keywords**: Scans L1 text for UI words ("File", "Help", "Library") to flag `ui_chrome`.

### Stage 3: Spatial Graph Construction (`stage3_graph_service.py`)
- **Pairwise Geometry**: Calculates `containment`, `overlap`, `alignment`, `proximity`, and `connector` (bridge) edges between all nodes.
- **O(N^2) Complexity**: Every node is compared against every other node.

### Stage 4: Grouping & Clustering (`stage4_grouping_service.py`)
- **Signals**: Groups elements using 6 signals: Semantic Anchors, Alignment/Spacing, Shared Parents, Overlap, Connector Topology, and UI Regions.
- **Output**: Produces `LogicalCluster` objects with MBB (Minimum Bounding Boxes).

### Stage 5: Container Synthesis (`stage5_container_service.py`)
- **Evidence Scoring**: Decides if a cluster is a "Container" based on: Grouped Children (0.25), Geometric Consistency (0.15), Visible Bounds (0.35), Graph Density (0.15), and Containment Graph (0.10).
- **Nesting**: Establishes initial nesting parents.

### Stage 6: Hierarchy Resolution (`stage6_hierarchy_service.py`)
- **Parenting Logic**: Assigns children to the smallest enclosing container parent.
- **Cycle Breaking**: Uses DFS to detect and prune parenting loops.
- **Sorting**: Enforces stable sibling order (Y then X).

### Stage 7: Cleanup & Validation (`stage7_cleanup_service.py`)
- **Redundant Wrappers**: Collapses containers with exactly one child that is also a container (area ratio > 0.90).
- **Tightening**: Shrinks container boxes to fit children plus padding.

---

## 2. Identified Section Types

| Section Type | Location / Component |
| :--- | :--- |
| **AI-Based** | `azure_service.py` (L1/L2 extraction), `stage1` (Snapping IoU), `stage2` (Keyword matching). |
| **Geometry-Based** | `stage1.5` (solidity, extent math), `stage3` (IoU, enclosure, centroid alignment), `stage6/7` (nesting math). |
| **Contour-Based** | `stage1` (RETR_EXTERNAL), `stage1.5` (RETR_TREE hierarchy), `stage1.75` (concentric collapsing). |
| **Grouping Logic** | `stage4` (clustering signals), `stage5` (evidence-based synthesis). |
| **Hierarchy Logic** | `stage6` (DAG reduction, cycle breaking), `stage7` (wrapper collapsing, box tightening). |

---

## 3. Why the Current Level 2 Struggles

### 3.1 Systematic Failure Modes
- **Aggressive Over-Pruning**: The logic to remove "Text-Edge Canny Artifacts" in Stage 1.75 is too aggressive. In flowcharts, process cards are often exactly sized to their text label. If the area ratio is $< 1.35$, the **entire process box is deleted**, leaving the text floating.
- **Geometric Rigidity**: Thresholds like `enclosure > 0.85` or `solidity > 0.95` fail on low-resolution or hand-drawn images where lines are fuzzy or slightly disconnected.
- **Hough Line Fragmentation**: Standard Hough transforms (Stage 1.5) often break a single long arrow into 3-4 disconnected segments, making connector synthesis brittle.
- **O(N^2) Scaling Risk**: As diagram complexity grows, Stage 3's pairwise comparisons and Stage 4's clustering logic slow down linearly, hitting CPU bottlenecks.

### 3.2 Duplicate Detections
- **Concentric Outlines**: Canny edge detection often produces two parallel lines for a single thick border. Stage 1.75 attempts to collapse these, but if the image is noisy, they remain as "double boxes" in the editor.
- **LMM vs CV Redundancy**: If an LMM graphic doesn't perfectly IoU-snap (> 0.5) to an OpenCV contour, **both** are kept. This creates "ghost shadows" in the editor where a pixel-perfect box sits under a fuzzy AI-detected one.

### 3.3 Instability in Hierarchy
- **Single-Child Paradox**: Stage 7 collapses redundant wrappers, but if the user *intended* to have a nested card (e.g. a "Service" card inside a "Module" card), the hierarchy logic might collapse them into one, losing the semantic grouping.
- **Floating Connectors**: Connectors (arrows) are currently not strictly "owned" by containers. If a user moves a container in the editor, the arrow stays behind because the hierarchy logic primarily focuses on containment, not connectivity.

### 3.4 Why Gliffy/Draw.io Screenshots Fail
- **Grid Interference**: Screenshots often contain faint grid backgrounds. Stage 1's adaptive thresholding treats these as "shapes", cluttering the graph with thousands of micro-rectangles.
- **UI Chrome Leakage**: Even with Stage 2's separation, toolbars and sidebars from the Gliffy interface often leak into the "Diagram Content" if they don't contain exact keywords, resulting in uneditable UI buttons on the slide.

---

## 4. Comparison: Current vs. Redesigned Redesign

| Feature | Current "Modular Hybrid" | Desired "Simple Flowchart-First" |
| :--- | :--- | :--- |
| **Primary Goal** | High-fidelity reconstruction of everything (Icons, UI, Containers, Diagrams). | **Stable, editable reconstruction of simple flowcharts/architecture diagrams.** |
| **Complexity** | 7-stage complex pipeline with hundreds of thresholds. | Focused, deterministic geometry-first snapping. |
| **AI Role** | Heavy reliance on recursive $O(N)$ LMM calls and semantic labels. | **AI provides "hints" and text labels; CV provides the physical structure.** |
| **User Intervention** | System tries to be "perfect" before user sees it. | **Prioritizes manual correction in the frontend editor.** |
| **Connector Logic** | Brittle line-segment grouping. | **First-class "Connector" objects that snap to "Container" ports.** |
| **Shape Types** | Tries to detect triangles, polygons, etc. | **Focuses on standard boxes, rounded cards, and directed arrows.** |

###Redesigned Priority: Simple Flowchart Reconstruction
The redesign will simplify the 7 stages into a more robust **Geometry-First** flow:
1. **L1 Anchor Sync**: L1 text is the absolute source of truth.
2. **Deterministic Box Snapping**: Snap the best-fitting OpenCV rectangle/rounded-rect to every L1 text anchor.
3. **Connectivity Snapping**: Use line-endpoint proximity to "bind" arrows to the boxes they touch.
4. **Editable JSON Layer Mapping**: Convert these directly into `container` and `connector` types that the React Konva editor understands natively.

---

## 5. Summary of Audit Findings

The current Level 2 implementation is **technically impressive but architecturally fragile**. It attempts to solve too much (UI Chrome, Icons, Layouts) using complex heuristics that fail on common diagram edge cases.

**Recommendation**: Pivot the Level 2 logic to treat **L1 Text as Gravity Anchors**. Instead of trying to "detect" shapes in isolation, the system should "seek" shapes that enclose known text labels, providing a much higher success rate for flowchart and architecture diagram reconstruction.
