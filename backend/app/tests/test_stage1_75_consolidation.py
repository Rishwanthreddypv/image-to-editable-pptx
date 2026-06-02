import os
import pytest
import cv2
import numpy as np
from app.services.stage1_5_reconstruction_service import ReconstructedPrimitive
from app.services.stage1_75_consolidation_service import stage1_75_consolidation_service
from app.schemas.layer import Layer, GeometryBase

@pytest.mark.asyncio
async def test_stage1_75_shape_consolidation():
    # 1. Setup temporary test image
    test_image_path = "test_stage1_75_temp.png"
    img = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    cv2.imwrite(test_image_path, img)

    # 2. Mock input L1 layers
    l1_layers = [
        Layer(
            id="text_1",
            type="text",
            geometry=GeometryBase(x=100.0, y=100.0, w=50.0, h=15.0),
            content={"text": "Inside Card"},
            parent_group_id=None,
            child_layer_ids=[]
        ),
        Layer(
            id="text_2",
            type="text",
            geometry=GeometryBase(x=500.0, y=500.0, w=30.0, h=10.0),
            content={"text": "Noise outline"},
            parent_group_id=None,
            child_layer_ids=[]
        )
    ]

    # 3. Create raw reconstructed primitives containing all noise/deduplication situations
    primitives = [
        # Normal text element
        ReconstructedPrimitive(
            id="text_prim_1",
            type="text",
            bbox={"x": 100.0, "y": 100.0, "w": 50.0, "h": 15.0},
            confidence=1.0,
            source_evidence=["ocr"],
            metadata={"original_layer_id": "text_1"}
        ),
        
        # A. Micro-rectangle (should be pruned)
        ReconstructedPrimitive(
            id="micro_shape",
            type="shape",
            bbox={"x": 10.0, "y": 10.0, "w": 5.0, "h": 5.0},
            confidence=0.40,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rectangle"}
        ),
        
        # B. Ultra-thin aspect ratio shape (should be pruned)
        ReconstructedPrimitive(
            id="thin_shape",
            type="shape",
            bbox={"x": 30.0, "y": 30.0, "w": 100.0, "h": 2.0},  # AR = 50.0 > 25.0
            confidence=0.45,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rectangle"}
        ),
        
        # C. Text-edge Canny outline artifact enclosing single text element perfectly (should be pruned)
        ReconstructedPrimitive(
            id="text_edge_noise_shape",
            type="shape",
            bbox={"x": 498.0, "y": 498.0, "w": 34.0, "h": 14.0},  # Tightly wraps text_2 (x=500, y=500, w=30, h=10)
            confidence=0.55,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rectangle"}
        ),

        # D. Concentric card border pair (should be collapsed into outer card)
        # Inner card border (should be collapsed)
        ReconstructedPrimitive(
            id="concentric_inner",
            type="shape",
            bbox={"x": 202.0, "y": 202.0, "w": 96.0, "h": 96.0},
            confidence=0.80,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rectangle", "associated_texts": ["text_1"]}
        ),
        # Outer card border (should be kept and confidence fused)
        ReconstructedPrimitive(
            id="concentric_outer",
            type="shape",
            bbox={"x": 200.0, "y": 200.0, "w": 100.0, "h": 100.0},
            confidence=0.90,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rounded_rectangle"}
        ),

        # E. Near-identical redundant shape detections (IoU > 0.85, should merge and keep higher confidence)
        ReconstructedPrimitive(
            id="duplicate_shape_1",
            type="shape",
            bbox={"x": 350.0, "y": 350.0, "w": 50.0, "h": 50.0},
            confidence=0.60,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rectangle"}
        ),
        ReconstructedPrimitive(
            id="duplicate_shape_2",
            type="shape",
            bbox={"x": 351.0, "y": 349.0, "w": 49.0, "h": 51.0},  # Massive IoU ~ 0.90
            confidence=0.85,
            source_evidence=["lmm_graphic"],
            metadata={"shape_type": "rounded_rectangle"}
        ),

        # F. Legitimate nested card (small card within larger panel - should NOT be collapsed or pruned)
        # Larger panel
        ReconstructedPrimitive(
            id="parent_panel",
            type="shape",
            bbox={"x": 50.0, "y": 50.0, "w": 300.0, "h": 300.0},
            confidence=0.95,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "panel"}
        ),
        # Nested card
        ReconstructedPrimitive(
            id="child_card",
            type="shape",
            bbox={"x": 70.0, "y": 70.0, "w": 80.0, "h": 80.0},  # Area ratio = 6400 / 90000 = 0.07 <= 0.80
            confidence=0.90,
            source_evidence=["opencv_contour"],
            metadata={"shape_type": "rounded_rectangle"}
        )
    ]

    try:
        # Run consolidation service
        consolidated = await stage1_75_consolidation_service.consolidate_primitives(
            primitives=primitives,
            image_path=test_image_path,
            project_id="test-proj-175",
            l1_layers=l1_layers,
            l2_graphics_candidates=[]
        )

        # 4. Assertions
        # Total final consolidated should be 5: text_prim_1, concentric_outer (merged), duplicate_shape_2 (merged), parent_panel, child_card
        assert len(consolidated) == 5

        # Extract IDs of final consolidated
        consolidated_ids = [c.id for c in consolidated]
        
        # Verify text was preserved
        assert "text_prim_1" in consolidated_ids
        
        # Verify micro shape was pruned
        assert "micro_shape" not in consolidated_ids
        
        # Verify thin shape was pruned
        assert "thin_shape" not in consolidated_ids
        
        # Verify text edge artifact shape was pruned
        assert "text_edge_noise_shape" not in consolidated_ids

        # Verify concentric border collapsed
        assert "concentric_inner" not in consolidated_ids
        assert "concentric_outer" in consolidated_ids
        outer_card = next(c for c in consolidated if c.id == "concentric_outer")
        # Confidence fused: 0.90 + 0.1 * 0.80 = 0.98
        assert outer_card.confidence == pytest.approx(0.98, abs=0.01)
        # Type should be rounded rectangle since s2 was rounded
        assert outer_card.metadata["shape_type"] == "rounded_rectangle"
        # Associated texts merged
        assert "text_1" in outer_card.metadata["associated_texts"]

        # Verify near-identical rectangle merged (prefer higher confidence)
        assert "duplicate_shape_1" not in consolidated_ids
        assert "duplicate_shape_2" in consolidated_ids
        dup_kept = next(c for c in consolidated if c.id == "duplicate_shape_2")
        # Confidence fused: 0.85 + 0.1 * 0.60 = 0.91
        assert dup_kept.confidence == pytest.approx(0.91, abs=0.01)
        # Source evidence combined
        assert "opencv_contour" in dup_kept.source_evidence
        assert "lmm_graphic" in dup_kept.source_evidence

        # Verify legitimate nesting conserved
        assert "parent_panel" in consolidated_ids
        assert "child_card" in consolidated_ids

        # Verify debug files created in workspace root
        assert os.path.exists("../debug_stage1_75_consolidated_test-proj-175.png")
        assert os.path.exists("../debug_stage1_75_dump_test-proj-175.json")

    finally:
        # 5. Cleanup temp files
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
        if os.path.exists("../debug_stage1_75_consolidated_test-proj-175.png"):
            os.remove("../debug_stage1_75_consolidated_test-proj-175.png")
        if os.path.exists("../debug_stage1_75_dump_test-proj-175.json"):
            os.remove("../debug_stage1_75_dump_test-proj-175.json")
