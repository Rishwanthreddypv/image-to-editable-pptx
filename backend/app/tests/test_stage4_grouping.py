import os
import json
import pytest
from app.services.stage4_grouping_service import stage4_grouping_service
from app.services.stage3_graph_service import SpatialGraph, GraphNode, GraphEdge

@pytest.mark.asyncio
async def test_stage4_grouping_logic():
    # 1. Construct a mock SpatialGraph
    # We will construct a scene with:
    # - A shape enclosing a text (containment_anchor)
    # - Three horizontally aligned shapes with consistent spacing (spatial_alignment, spacing_consistency)
    # - Two vertical aligned shapes with no other neighbors (low_confidence_pair)
    # - A connector linking two shapes
    
    nodes = [
        # Enclosure Pair
        GraphNode(id="shape_parent", type="shape", classification="diagram_content", bbox={"x": 100.0, "y": 100.0, "w": 200.0, "h": 150.0}),
        GraphNode(id="text_child", type="text", classification="diagram_content", bbox={"x": 120.0, "y": 120.0, "w": 80.0, "h": 30.0}),
        
        # Horizontal Aligned Chain (Consistent Spacing: gap of 50px between each)
        # N0: 400..500
        # N1: 550..650 (gap of 50px)
        # N2: 700..800 (gap of 50px)
        GraphNode(id="align_h0", type="shape", classification="diagram_content", bbox={"x": 400.0, "y": 300.0, "w": 100.0, "h": 50.0}),
        GraphNode(id="align_h1", type="shape", classification="diagram_content", bbox={"x": 550.0, "y": 300.0, "w": 100.0, "h": 50.0}),
        GraphNode(id="align_h2", type="shape", classification="diagram_content", bbox={"x": 700.0, "y": 300.0, "w": 100.0, "h": 50.0}),
        
        # Vertical Aligned Pair
        GraphNode(id="align_v0", type="shape", classification="diagram_content", bbox={"x": 900.0, "y": 100.0, "w": 100.0, "h": 50.0}),
        GraphNode(id="align_v1", type="shape", classification="diagram_content", bbox={"x": 900.0, "y": 200.0, "w": 100.0, "h": 50.0}),
        
        # Connector Link
        GraphNode(id="conn_shape1", type="shape", classification="diagram_content", bbox={"x": 100.0, "y": 500.0, "w": 80.0, "h": 80.0}),
        GraphNode(id="conn_shape2", type="shape", classification="diagram_content", bbox={"x": 300.0, "y": 500.0, "w": 80.0, "h": 80.0}),
        GraphNode(id="connector_line", type="connector", classification="diagram_content", bbox={"x": 180.0, "y": 540.0, "w": 120.0, "h": 2.0})
    ]

    edges = [
        # Containment Edge
        GraphEdge(source="shape_parent", target="text_child", type="containment", confidence=1.0),
        
        # Horizontal Alignment Edges
        GraphEdge(source="align_h0", target="align_h1", type="alignment", confidence=1.0, metadata={"alignment_direction": "horizontal"}),
        GraphEdge(source="align_h1", target="align_h2", type="alignment", confidence=1.0, metadata={"alignment_direction": "horizontal"}),
        GraphEdge(source="align_h0", target="align_h2", type="alignment", confidence=1.0, metadata={"alignment_direction": "horizontal"}),
        
        # Vertical Alignment Edges (Pair only)
        GraphEdge(source="align_v0", target="align_v1", type="alignment", confidence=1.0, metadata={"alignment_direction": "vertical"}),
        
        # Connector Edge
        GraphEdge(source="conn_shape1", target="conn_shape2", type="connector", confidence=0.9, metadata={"connector_id": "connector_line"})
    ]

    spatial_graph = SpatialGraph(
        project_id="test_grouping_project",
        nodes=nodes,
        edges=edges
    )

    # 2. Create a dummy image file so opencv doesn't crash on load (or handles it gracefully)
    import cv2
    import numpy as np
    dummy_img_path = "test_grouping_dummy.png"
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    cv2.imwrite(dummy_img_path, img)

    try:
        # 3. Execute Grouping Service
        clusters = await stage4_grouping_service.group_logical_clusters(
            spatial_graph=spatial_graph,
            image_path=dummy_img_path,
            project_id="test_grouping_project"
        )

        assert len(clusters) > 0, "Should successfully create logical clusters"
        
        # Verify Containment Cluster
        containment_cluster = next((c for c in clusters if "CONTAINMENT_ANCHOR" in c.reason_codes), None)
        assert containment_cluster is not None, "Containment cluster should be detected"
        assert "shape_parent" in containment_cluster.members
        assert "text_child" in containment_cluster.members
        assert containment_cluster.confidence == 0.95
        
        # Verify Horizontal Spacing Consistency Cluster
        horizontal_chain = next((c for c in clusters if "SPACING_CONSISTENCY" in c.reason_codes), None)
        assert horizontal_chain is not None, "Horizontal chain with spacing consistency should be detected"
        assert "align_h0" in horizontal_chain.members
        assert "align_h1" in horizontal_chain.members
        assert "align_h2" in horizontal_chain.members
        assert horizontal_chain.confidence >= 0.85
        
        # Verify Vertical Low-Confidence Pair Cluster
        vertical_pair = next((c for c in clusters if "LOW_CONFIDENCE_PAIR" in c.reason_codes), None)
        assert vertical_pair is not None, "Vertical alignment pair should be preserved as low confidence"
        assert "align_v0" in vertical_pair.members
        assert "align_v1" in vertical_pair.members
        assert vertical_pair.confidence == 0.55
        
        # Verify Connector Flow Cluster
        connector_cluster = next((c for c in clusters if "CONNECTOR_LINK" in c.reason_codes), None)
        assert connector_cluster is not None, "Connector cluster should be detected"
        assert "conn_shape1" in connector_cluster.members
        assert "conn_shape2" in connector_cluster.members
        assert "connector_line" in connector_cluster.members
        assert connector_cluster.confidence == 0.9

        # Verify JSON Metadata Export
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage4_metadata_test_grouping_project.json")
        assert os.path.exists(metadata_file), "JSON metadata should be exported to project root"
        
        with open(metadata_file, "r") as f:
            meta = json.load(f)
            assert meta["project_id"] == "test_grouping_project"
            assert meta["total_clusters"] == len(clusters)

        # Verify visual debug image exists
        debug_img_file = os.path.join(project_root, "debug_stage4_clusters_test_grouping_project.png")
        assert os.path.exists(debug_img_file), "Visual debug overlay PNG should be exported to project root"

    finally:
        # Cleanup
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage4_metadata_test_grouping_project.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        debug_img_file = os.path.join(project_root, "debug_stage4_clusters_test_grouping_project.png")
        if os.path.exists(debug_img_file):
            os.remove(debug_img_file)
