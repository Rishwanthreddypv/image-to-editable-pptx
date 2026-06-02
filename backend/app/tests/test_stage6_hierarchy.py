import os
import json
import pytest
import cv2
import numpy as np
from app.services.stage3_graph_service import SpatialGraph, GraphNode, GraphEdge
from app.services.stage5_container_service import SynthesizedContainer
from app.services.stage6_hierarchy_service import stage6_hierarchy_service, HierarchyTree, HierarchyNode

@pytest.mark.asyncio
async def test_stage6_hierarchy_logic():
    # 1. Setup mock Stage 5 Synthesized Containers
    containers = [
        # Outer Backdrop
        SynthesizedContainer(
            container_id="container_5_outer",
            members=["container_5_inner", "node_shape_a", "node_text_a"],
            bbox={"x": 100.0, "y": 100.0, "w": 500.0, "h": 400.0},
            confidence=0.95,
            evidence_sources=["VISIBLE_BOUNDS", "GROUPED_CHILDREN"],
            is_low_confidence=False
        ),
        # Inner Card (Nested inside Outer Backdrop)
        SynthesizedContainer(
            container_id="container_5_inner",
            members=["node_shape_a", "node_text_a"],
            bbox={"x": 150.0, "y": 120.0, "w": 300.0, "h": 200.0},
            confidence=0.90,
            evidence_sources=["VISIBLE_BOUNDS"],
            is_low_confidence=False,
            nested_parent_id="container_5_outer"
        ),
        # A sibling overlapping container to test deterministic resolution
        SynthesizedContainer(
            container_id="container_5_sibling",
            members=["node_shape_b"],
            bbox={"x": 580.0, "y": 100.0, "w": 200.0, "h": 200.0},
            confidence=0.85,
            evidence_sources=["GEOMETRIC_CONSISTENCY"],
            is_low_confidence=True
        )
    ]

    # 2. Setup mock SpatialGraph Nodes (Stage 3)
    nodes = [
        # Atomic elements inside the Inner Container
        GraphNode(id="node_shape_a", type="shape", classification="diagram_content", bbox={"x": 180.0, "y": 140.0, "w": 100.0, "h": 80.0}),
        GraphNode(id="node_text_a", type="text", classification="diagram_content", bbox={"x": 190.0, "y": 230.0, "w": 80.0, "h": 30.0}),
        
        # Atomic element inside the Sibling Container
        GraphNode(id="node_shape_b", type="shape", classification="diagram_content", bbox={"x": 600.0, "y": 120.0, "w": 100.0, "h": 80.0}),

        # UI Chrome / noise nodes (should be excluded by separating priors in Stage 6)
        GraphNode(id="toolbar_btn_zoom", type="shape", classification="toolbar", bbox={"x": 10.0, "y": 10.0, "w": 30.0, "h": 30.0}),
        GraphNode(id="sidebar_bg", type="shape", classification="sidebar", bbox={"x": 0.0, "y": 0.0, "w": 80.0, "h": 720.0})
    ]

    spatial_graph = SpatialGraph(
        project_id="test_stage6_project",
        nodes=nodes,
        edges=[]
    )

    # 3. Create dummy image
    dummy_img_path = "test_stage6_dummy.png"
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    cv2.imwrite(dummy_img_path, img)

    try:
        # 4. Execute Hierarchy Resolution
        tree = await stage6_hierarchy_service.resolve_hierarchy(
            synthesized_containers=containers,
            spatial_graph=spatial_graph,
            image_path=dummy_img_path,
            project_id="test_stage6_project"
        )

        # 5. Asserts & Validations
        assert tree is not None, "HierarchyTree should be returned"
        assert tree.total_nodes > 0
        
        # Verify that UI chrome is pruned/excluded
        assert "toolbar_btn_zoom" not in tree.nodes, "UI Toolbar elements should be pruned from active layout tree"
        assert "sidebar_bg" not in tree.nodes, "UI Sidebar elements should be pruned from active layout tree"

        # Verify Geometric Containment & Nesting
        outer_node = tree.nodes.get("container_5_outer")
        inner_node = tree.nodes.get("container_5_inner")
        sibling_node = tree.nodes.get("container_5_sibling")
        node_shape_a = tree.nodes.get("node_shape_a")
        node_text_a = tree.nodes.get("node_text_a")
        node_shape_b = tree.nodes.get("node_shape_b")

        assert outer_node is not None
        assert inner_node is not None
        assert node_shape_a is not None
        assert node_text_a is not None
        assert node_shape_b is not None

        # Outer should be the parent of inner
        assert inner_node.parent_id == "container_5_outer", "Inner container must be nested inside Outer container"
        assert "container_5_inner" in outer_node.child_ids, "Outer container must list inner container as child"

        # Transitive parenting reduction:
        # node_shape_a is geometrically inside both outer (100, 100) and inner (150, 120).
        # It must be parented by inner_node (the smallest enclosing parent), NOT outer_node directly!
        assert node_shape_a.parent_id == "container_5_inner", "Atomic element must be parented by direct inner container, not transitive grandparent"
        assert "node_shape_a" in inner_node.child_ids
        assert "node_shape_a" not in outer_node.child_ids, "Transitive parent link from outer container must be pruned"

        # Check node_text_a parenting (nested inside inner)
        assert node_text_a.parent_id == "container_5_inner"
        assert "node_text_a" in inner_node.child_ids

        # Check sibling container elements
        assert node_shape_b.parent_id == "container_5_sibling"

        # Verify Sibling Stable Sorting
        # For inner_node: children are node_shape_a (y=140) and node_text_a (y=230)
        # They should be sorted Top-to-Bottom: node_shape_a first, then node_text_a.
        assert inner_node.child_ids == ["node_shape_a", "node_text_a"], "Siblings must be sorted deterministically by Y coordinate"

        # 6. Verify Cycle Detection & Breaking
        # Let's construct a circular parenting structure manually on a copy of nodes and test breaking
        cyclic_nodes = {
            "A": HierarchyNode(
                node_id="A", type="container", bbox={"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5},
                parent_id="B", confidence=0.9, is_low_confidence=False
            ),
            "B": HierarchyNode(
                node_id="B", type="container", bbox={"x": 0.0, "y": 0.0, "w": 0.4, "h": 0.4},
                parent_id="C", confidence=0.8, is_low_confidence=False
            ),
            "C": HierarchyNode(
                node_id="C", type="container", bbox={"x": 0.0, "y": 0.0, "w": 0.3, "h": 0.3},
                parent_id="A", confidence=0.7, is_low_confidence=False  # lowest confidence
            )
        }
        stage6_hierarchy_service._validate_and_break_cycles(cyclic_nodes)
        
        # Cycle B -> C -> A -> B should be broken at the lowest confidence edge (C's parent_id = "A" with conf=0.7)
        assert cyclic_nodes["C"].parent_id is None, "Circular parenting cycle must be broken at the lowest confidence edge"
        assert cyclic_nodes["A"].parent_id == "B", "Other edges in the cycle should remain untouched"
        assert cyclic_nodes["B"].parent_id == "C"

        # 7. Verify JSON Metadata Export
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage6_hierarchy_test_stage6_project.json")
        assert os.path.exists(metadata_file), "JSON hierarchy tree metadata should be written to project root"
        
        with open(metadata_file, "r") as f:
            meta = json.load(f)
            assert meta["project_id"] == "test_stage6_project"
            assert meta["total_nodes"] == len(tree.nodes)

        # Verify visual debug image exists
        debug_img_file = os.path.join(project_root, "debug_stage6_hierarchy_test_stage6_project.png")
        assert os.path.exists(debug_img_file), "Visual debug overlay PNG should be written to project root"

    finally:
        # Cleanup
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage6_hierarchy_test_stage6_project.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        debug_img_file = os.path.join(project_root, "debug_stage6_hierarchy_test_stage6_project.png")
        if os.path.exists(debug_img_file):
            os.remove(debug_img_file)
