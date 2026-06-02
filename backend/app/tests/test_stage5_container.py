import os
import json
import pytest
from app.services.stage3_graph_service import SpatialGraph, GraphNode, GraphEdge
from app.services.stage4_grouping_service import LogicalCluster
from app.services.stage5_container_service import stage5_container_service, SynthesizedContainer

@pytest.mark.asyncio
async def test_stage5_container_synthesis_logic():
    # 1. Setup mock SpatialGraph Nodes
    nodes = [
        # Outer Container Group (Large backdrop)
        GraphNode(id="backdrop_shape", type="shape", classification="background", bbox={"x": 100.0, "y": 100.0, "w": 400.0, "h": 300.0}),
        
        # Inner Container Group (Enclosed inside backdrop)
        GraphNode(id="inner_card_shape", type="shape", classification="diagram_content", bbox={"x": 150.0, "y": 120.0, "w": 200.0, "h": 150.0}),
        GraphNode(id="label_a", type="text", classification="diagram_content", bbox={"x": 170.0, "y": 140.0, "w": 100.0, "h": 25.0}),
        GraphNode(id="label_b", type="text", classification="diagram_content", bbox={"x": 170.0, "y": 180.0, "w": 100.0, "h": 25.0}),
        
        # Unrelated aligned elements (Low-confidence candidate)
        GraphNode(id="align_x", type="shape", classification="diagram_content", bbox={"x": 600.0, "y": 100.0, "w": 80.0, "h": 80.0}),
        GraphNode(id="align_y", type="shape", classification="diagram_content", bbox={"x": 750.0, "y": 100.0, "w": 80.0, "h": 80.0}),
        
        # Weak noise candidate (Single element with no boundary or relationships)
        GraphNode(id="noise_element", type="shape", classification="unknown", bbox={"x": 900.0, "y": 500.0, "w": 50.0, "h": 50.0})
    ]

    edges = [
        # Outer enclosing inner
        GraphEdge(source="backdrop_shape", target="inner_card_shape", type="containment", confidence=1.0),
        GraphEdge(source="backdrop_shape", target="label_a", type="containment", confidence=1.0),
        GraphEdge(source="backdrop_shape", target="label_b", type="containment", confidence=1.0),
        
        # Inner container enclosing labels
        GraphEdge(source="inner_card_shape", target="label_a", type="containment", confidence=1.0),
        GraphEdge(source="inner_card_shape", target="label_b", type="containment", confidence=1.0),
        
        # Proximity and alignment for inner items
        GraphEdge(source="label_a", target="label_b", type="alignment", confidence=1.0, metadata={"alignment_direction": "vertical"}),
        
        # Alignment for low confidence pair
        GraphEdge(source="align_x", target="align_y", type="alignment", confidence=0.8, metadata={"alignment_direction": "horizontal"})
    ]

    spatial_graph = SpatialGraph(
        project_id="test_container_project",
        nodes=nodes,
        edges=edges
    )

    # 2. Setup mock Stage 4 Logical Clusters
    logical_clusters = [
        # Cluster 0: Inner Card Group (Full evidence: Grouped Children, Aspect Ratio, Visible Boundary, Graph Density, Containment)
        LogicalCluster(
            cluster_id="cluster_4_0",
            members=["inner_card_shape", "label_a", "label_b"],
            bbox={"x": 150.0, "y": 120.0, "w": 200.0, "h": 150.0},
            confidence=0.95,
            reason_codes=["CONTAINMENT_ANCHOR", "SPATIAL_ALIGNMENT", "SPACING_CONSISTENCY"]
        ),
        
        # Cluster 1: Outer Backdrop Group (Full evidence)
        LogicalCluster(
            cluster_id="cluster_4_1",
            members=["backdrop_shape", "inner_card_shape", "label_a", "label_b"],
            bbox={"x": 100.0, "y": 100.0, "w": 400.0, "h": 300.0},
            confidence=0.90,
            reason_codes=["SHARED_BACKGROUND", "CONTOUR_ENCLOSURE"]
        ),
        
        # Cluster 2: Align Pair (Partial evidence: Grouped children, aspect ratio, alignment, but NO boundary, NO containment)
        # Should yield low-confidence container
        LogicalCluster(
            cluster_id="cluster_4_2",
            members=["align_x", "align_y"],
            bbox={"x": 600.0, "y": 100.0, "w": 230.0, "h": 80.0},
            confidence=0.55,
            reason_codes=["SPATIAL_ALIGNMENT"]
        ),
        
        # Cluster 3: Weak Noise (0 layout density, 0 boundaries, aspect ratio OK but no child groups)
        # Should be discarded completely to protect against over-grouping
        LogicalCluster(
            cluster_id="cluster_4_3",
            members=["noise_element"],
            bbox={"x": 900.0, "y": 500.0, "w": 50.0, "h": 50.0},
            confidence=0.20,
            reason_codes=["SINGLETON"]
        )
    ]

    # Create a dummy white background image for drawing overlays
    import cv2
    import numpy as np
    dummy_img_path = "test_container_dummy.png"
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    cv2.imwrite(dummy_img_path, img)

    try:
        # 3. Execute Container Synthesis
        containers = await stage5_container_service.synthesize_containers(
            logical_clusters=logical_clusters,
            spatial_graph=spatial_graph,
            image_path=dummy_img_path,
            project_id="test_container_project"
        )

        # 4. Asserts & Validations
        assert len(containers) > 0, "Should synthesize valid containers"
        
        # Find Outer and Inner synthesized containers
        outer_c = next((c for c in containers if c.bbox["w"] == 400.0), None)
        inner_c = next((c for c in containers if c.bbox["w"] == 200.0), None)
        low_conf_c = next((c for c in containers if c.bbox["w"] == 230.0), None)
        noise_c = next((c for c in containers if c.bbox["w"] == 50.0), None)

        # Outer Backdrop assertions
        assert outer_c is not None, "Outer backdrop container should be synthesized"
        assert outer_c.is_low_confidence is False, "Outer backdrop container should be high confidence"
        assert "VISIBLE_BOUNDS" in outer_c.evidence_sources
        
        # Inner Card assertions
        assert inner_c is not None, "Inner card container should be synthesized"
        assert inner_c.is_low_confidence is False, "Inner card container should be high confidence"
        
        # Nested hierarchy assertions
        assert inner_c.nested_parent_id == outer_c.container_id, "Inner container should recognize outer container as parent"
        assert inner_c.container_id in outer_c.child_container_ids, "Outer container should record inner container in child_container_ids"

        # Low confidence group assertions
        assert low_conf_c is not None, "Low confidence aligned container should be preserved"
        assert low_conf_c.is_low_confidence is True, "Alignment pair without boundaries should remain low-confidence"
        assert "VISIBLE_BOUNDS" not in low_conf_c.evidence_sources, "Low confidence alignment should lack visible bounds"

        # Over-grouping shield assertions (Noise discarded)
        assert noise_c is None, "Weak noise container should be discarded by the over-grouping shield"

        # Verify JSON Metadata Export
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage5_metadata_test_container_project.json")
        assert os.path.exists(metadata_file), "JSON metadata should be exported to project root"
        
        with open(metadata_file, "r") as f:
            meta = json.load(f)
            assert meta["project_id"] == "test_container_project"
            assert meta["total_containers_synthesized"] == len(containers)

        # Verify visual debug image exists
        debug_img_file = os.path.join(project_root, "debug_stage5_containers_test_container_project.png")
        assert os.path.exists(debug_img_file), "Visual debug overlay PNG should be exported to project root"

    finally:
        # Cleanup
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage5_metadata_test_container_project.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        debug_img_file = os.path.join(project_root, "debug_stage5_containers_test_container_project.png")
        if os.path.exists(debug_img_file):
            os.remove(debug_img_file)
