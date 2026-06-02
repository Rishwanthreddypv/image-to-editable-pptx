import os
import pytest
import cv2
import numpy as np
from app.services.stage1_extraction_service import AtomicObject
from app.services.stage1_5_reconstruction_service import stage1_5_reconstruction_service
from app.schemas.layer import Layer, GeometryBase

@pytest.mark.asyncio
async def test_stage1_5_shape_and_connector_reconstruction():
    # 1. Setup a temporary test image with geometric drawings (a rectangle, a rounded rect, and arrows)
    test_image_path = "test_stage1_5_temp.png"
    
    # Create white canvas
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    
    # Draw a solid black rectangle
    cv2.rectangle(img, (200, 150), (450, 250), (0, 0, 0), 2)
    
    # Draw a solid horizontal line (shaft) and a triangular arrowhead at the end
    cv2.line(img, (500, 200), (700, 200), (0, 0, 0), 2)
    # Draw a simple triangle arrowhead pointing right
    ah_pts = np.array([[690, 190], [710, 200], [690, 210]], dtype=np.int32)
    cv2.drawContours(img, [ah_pts], -1, (0, 0, 0), -1)

    # Draw a dashed line (multiple short segments)
    for step in range(250, 490, 40):
        cv2.line(img, (800, step), (800, step + 20), (0, 0, 0), 2)

    cv2.imwrite(test_image_path, img)

    # Mock Stage 1 input AtomicObjects
    atomic_objects = [
        AtomicObject(
            id="atomic_text_1",
            type="text",
            bbox={"x": 220.0, "y": 180.0, "w": 100.0, "h": 30.0},
            confidence=1.0,
            source_evidence=["ocr"],
            metadata={"original_layer_id": "l1_layer_text"}
        )
    ]

    l1_layers = [
        Layer(
            id="l1_layer_text",
            type="text",
            geometry=GeometryBase(x=220.0, y=180.0, w=100.0, h=30.0),
            content={"text": "Process Node 1"},
            parent_group_id=None,
            child_layer_ids=[]
        )
    ]

    l2_graphics_candidates = [
        Layer(
            id="l2_lmm_gfx_1",
            type="image",
            geometry=GeometryBase(x=198.0, y=148.0, w=254.0, h=104.0),
            content={"label": "card", "semantic_role": "CARD"},
            parent_group_id=None,
            child_layer_ids=[]
        )
    ]

    try:
        # 2. Run Stage 1.5 Reconstruction Service
        reconstructed = await stage1_5_reconstruction_service.reconstruct_shapes_and_connectors(
            atomic_objects=atomic_objects,
            image_path=test_image_path,
            project_id="test-proj-15",
            l1_layers=l1_layers,
            l2_graphics_candidates=l2_graphics_candidates
        )

        assert len(reconstructed) > 0
        
        # Verify L1 text was preserved
        text_nodes = [r for r in reconstructed if r.type == "text"]
        assert len(text_nodes) == 1
        assert text_nodes[0].metadata["original_layer_id"] == "l1_layer_text"

        # Verify shapes were detected (OpenCV contour rectangle + AI co-evidence)
        shape_nodes = [r for r in reconstructed if r.type == "shape"]
        assert len(shape_nodes) >= 1
        
        # Verify arrow connector was detected and constructed
        connector_nodes = [r for r in reconstructed if r.type == "connector"]
        assert len(connector_nodes) >= 1
        
        # Verify dashed style exists in metadata of at least one connector
        has_dashed = any(c.metadata.get("style") == "dashed" for c in connector_nodes)
        assert has_dashed is True

        # Verify debug outputs exist
        assert os.path.exists("../debug_stage1_5_reconstructed_test-proj-15.png")
        assert os.path.exists("../debug_stage1_5_dump_test-proj-15.json")

    finally:
        # Cleanup temp files
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
        if os.path.exists("../debug_stage1_5_reconstructed_test-proj-15.png"):
            os.remove("../debug_stage1_5_reconstructed_test-proj-15.png")
        if os.path.exists("../debug_stage1_5_dump_test-proj-15.json"):
            os.remove("../debug_stage1_5_dump_test-proj-15.json")
