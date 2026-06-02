import os
import json
import pytest
import cv2
import numpy as np
from app.services.stage6_hierarchy_service import HierarchyTree, HierarchyNode
from app.services.stage7_cleanup_service import stage7_cleanup_service

@pytest.mark.asyncio
async def test_stage7_cleanup_and_validation():
    # 1. Setup mock HierarchyTree nodes representing different cleanup test cases
    nodes = {
        # --- CASE A: Duplicate Containers (c_dup1 and c_dup2 have 90% overlap) ---
        "c_dup1": HierarchyNode(
            node_id="c_dup1",
            type="container",
            bbox={"x": 0.10, "y": 0.10, "w": 0.30, "h": 0.30},
            confidence=0.90,
            is_low_confidence=False,
            child_ids=["node_text_dup"],
            parent_id=None
        ),
        "c_dup2": HierarchyNode(
            node_id="c_dup2",
            type="container",
            bbox={"x": 0.105, "y": 0.105, "w": 0.29, "h": 0.29},
            confidence=0.80,  # lower confidence
            is_low_confidence=False,
            child_ids=["node_text_dup"],
            parent_id=None
        ),
        "node_text_dup": HierarchyNode(
            node_id="node_text_dup",
            type="text",
            bbox={"x": 0.15, "y": 0.15, "w": 0.10, "h": 0.05},
            confidence=0.95,
            is_low_confidence=False,
            child_ids=[],
            parent_id="c_dup2"  # parented by the duplicate that gets removed
        ),

        # --- CASE B: Bounding Box Tightening ---
        # Large container enclosing two far-spaced shapes. BBox should shrink to fit them + padding.
        "c_large": HierarchyNode(
            node_id="c_large",
            type="container",
            bbox={"x": 0.40, "y": 0.40, "w": 0.50, "h": 0.50},
            confidence=0.95,
            is_low_confidence=False,
            child_ids=["node_shape1", "node_shape2"],
            parent_id=None
        ),
        "node_shape1": HierarchyNode(
            node_id="node_shape1",
            type="shape",
            bbox={"x": 0.50, "y": 0.50, "w": 0.08, "h": 0.08},
            confidence=0.90,
            is_low_confidence=False,
            child_ids=[],
            parent_id="c_large"
        ),
        "node_shape2": HierarchyNode(
            node_id="node_shape2",
            type="shape",
            bbox={"x": 0.65, "y": 0.55, "w": 0.10, "h": 0.10},
            confidence=0.90,
            is_low_confidence=False,
            child_ids=[],
            parent_id="c_large"
        ),

        # --- CASE C: Redundant Wrapper Collapsing (c_wrap wraps c_wrapped_inner) ---
        "c_wrap_parent": HierarchyNode(
            node_id="c_wrap_parent",
            type="container",
            bbox={"x": 0.0, "y": 0.70, "w": 0.30, "h": 0.30},
            confidence=0.95,
            is_low_confidence=False,
            child_ids=["c_wrap"],
            parent_id=None
        ),
        "c_wrap": HierarchyNode(
            node_id="c_wrap",
            type="container",
            bbox={"x": 0.02, "y": 0.72, "w": 0.25, "h": 0.25},
            confidence=0.85,
            is_low_confidence=False,
            child_ids=["c_wrapped_inner"],
            parent_id="c_wrap_parent"
        ),
        "c_wrapped_inner": HierarchyNode(
            node_id="c_wrapped_inner",
            type="container",
            bbox={"x": 0.022, "y": 0.722, "w": 0.24, "h": 0.24},  # area ratio 0.24*0.24 / 0.25*0.25 = 0.92
            confidence=0.95,
            is_low_confidence=False,
            child_ids=["node_shape_wrapped"],
            parent_id="c_wrap"
        ),
        "node_shape_wrapped": HierarchyNode(
            node_id="node_shape_wrapped",
            type="shape",
            bbox={"x": 0.05, "y": 0.75, "w": 0.10, "h": 0.10},
            confidence=0.90,
            is_low_confidence=False,
            child_ids=[],
            parent_id="c_wrapped_inner"
        ),

        # --- CASE D: Physical Noise Deletion vs. Weak Container Downgrading ---
        # 1. Extremely small node -> should be deleted
        "tiny_noise_shape": HierarchyNode(
            node_id="tiny_noise_shape",
            type="shape",
            bbox={"x": 0.01, "y": 0.01, "w": 0.003, "h": 0.004},  # < 0.005 threshold
            confidence=0.90,
            is_low_confidence=False,
            child_ids=[],
            parent_id=None
        ),
        # 2. Large empty container with medium confidence -> should be downgraded, not deleted
        "c_empty_weak": HierarchyNode(
            node_id="c_empty_weak",
            type="container",
            bbox={"x": 0.80, "y": 0.05, "w": 0.15, "h": 0.15},
            confidence=0.48,  # weak confidence
            is_low_confidence=False,
            child_ids=[],
            parent_id=None
        ),
        # 3. Small empty container with low confidence -> should be deleted
        "c_empty_tiny_low": HierarchyNode(
            node_id="c_empty_tiny_low",
            type="container",
            bbox={"x": 0.95, "y": 0.01, "w": 0.004, "h": 0.004},
            confidence=0.20,
            is_low_confidence=True,
            child_ids=[],
            parent_id=None
        )
    }

    tree = HierarchyTree(
        project_id="test_stage7_project",
        total_nodes=len(nodes),
        nodes=nodes
    )

    # Create dummy image
    dummy_img_path = "test_stage7_dummy.png"
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    cv2.imwrite(dummy_img_path, img)

    try:
        # 2. Execute Stage 7 Cleanup & Validation
        cleaned_tree = await stage7_cleanup_service.clean_and_validate_hierarchy(
            hierarchy_tree=tree,
            image_path=dummy_img_path,
            project_id="test_stage7_project"
        )

        # 3. Validate Case A: Duplicate Deduplication
        assert "c_dup2" not in cleaned_tree.nodes, "c_dup2 has lower confidence and must be removed as a duplicate"
        assert "c_dup1" in cleaned_tree.nodes, "c_dup1 has higher confidence and must be kept"
        
        # Verify children are migrated correctly
        node_text_dup = cleaned_tree.nodes.get("node_text_dup")
        assert node_text_dup is not None
        assert node_text_dup.parent_id == "c_dup1", "Child of deleted duplicate container must migrate to the kept container parent"
        assert "node_text_dup" in cleaned_tree.nodes["c_dup1"].child_ids

        # 4. Validate Case B: Bounding Box Tightening
        c_large = cleaned_tree.nodes.get("c_large")
        assert c_large is not None
        # Original: x=0.40, y=0.40, w=0.50, h=0.50
        # Children union: min_x=0.50, min_y=0.50, max_x=0.75, max_y=0.65
        # With padding 0.01: min_x-padding=0.49, min_y-padding=0.49, max_x+padding=0.76, max_y+padding=0.66
        # Expected: x=0.49, y=0.49, w=0.27, h=0.17
        assert abs(c_large.bbox["x"] - 0.49) <= 0.001
        assert abs(c_large.bbox["y"] - 0.49) <= 0.001
        assert abs(c_large.bbox["w"] - 0.27) <= 0.001
        assert abs(c_large.bbox["h"] - 0.17) <= 0.001

        # 5. Validate Case C: Redundant Wrapper Collapsing
        # c_wrap parent wraps c_wrap, which wraps c_wrapped_inner.
        # Area ratio between c_wrapped_inner and c_wrap is > 0.90, so c_wrap must be collapsed!
        assert "c_wrap" not in cleaned_tree.nodes, "c_wrap must be collapsed as a redundant single-child container wrapper"
        c_wrapped_inner = cleaned_tree.nodes.get("c_wrapped_inner")
        assert c_wrapped_inner is not None
        # c_wrapped_inner should be parented by c_wrap's original parent (c_wrap_parent)
        assert c_wrapped_inner.parent_id == "c_wrap_parent", "Collapsed wrapper child must be parented by the wrapper parent"
        assert "c_wrapped_inner" in cleaned_tree.nodes["c_wrap_parent"].child_ids

        # 6. Validate Case D: Noise Deletion vs. Downgrading
        assert "tiny_noise_shape" not in cleaned_tree.nodes, "Tiny noise shapes (< 0.005) must be deleted"
        assert "c_empty_tiny_low" not in cleaned_tree.nodes, "Small empty low-confidence containers must be deleted"
        
        c_empty_weak = cleaned_tree.nodes.get("c_empty_weak")
        assert c_empty_weak is not None, "Large empty containers should be preserved"
        assert c_empty_weak.is_low_confidence is True, "Large empty container must be downgraded to low confidence"
        assert c_empty_weak.confidence == 0.30, "Large empty container confidence must be downgraded to 0.30"

        # 7. Verify JSON Metadata Export
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage7_cleaned_test_stage7_project.json")
        assert os.path.exists(metadata_file), "Cleaned JSON hierarchy metadata should be written to project root"
        
        # Verify visual debug image exists
        debug_img_file = os.path.join(project_root, "debug_stage7_cleaned_test_stage7_project.png")
        assert os.path.exists(debug_img_file), "Cleaned visual debug overlay PNG should be written to project root"

    finally:
        # Cleanup
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        metadata_file = os.path.join(project_root, "debug_stage7_cleaned_test_stage7_project.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        debug_img_file = os.path.join(project_root, "debug_stage7_cleaned_test_stage7_project.png")
        if os.path.exists(debug_img_file):
            os.remove(debug_img_file)
