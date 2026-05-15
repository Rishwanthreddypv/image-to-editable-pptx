from typing import List
from app.schemas.ocr import OCRResult
from app.schemas.layout import LayoutResult
from app.schemas.layer import Layer, GeometryBase

class DocumentBuilderService:
    def build_layers(self, ocr: OCRResult, layout: LayoutResult) -> List[Layer]:
        """
        Merge OCR and Layout results into a unified list of Document Layers.
        """
        layers = []
        
        # For simplicity, we'll use Layout elements as the primary structure
        # and attach OCR text to corresponding text elements.
        for i, element in enumerate(layout.elements):
            layer_type = self._map_type(element.type)
            
            content = {}
            if layer_type == "text":
                content["text"] = self._find_text_for_box(element, ocr)
            elif layer_type == "table":
                content["cells"] = [
                    {"rowIndex": 0, "colIndex": 0, "content": "Mock A1"},
                    {"rowIndex": 0, "colIndex": 1, "content": "Mock B1"},
                    {"rowIndex": 1, "colIndex": 0, "content": "Mock A2"},
                    {"rowIndex": 1, "colIndex": 1, "content": "Mock B2"}
                ]
            elif layer_type == "image":
                content["image_ref"] = f"crop_{i}.png"
            
            layers.append(Layer(
                id=f"layer_{i}",
                type=layer_type,
                geometry=GeometryBase(
                    x=element.x,
                    y=element.y,
                    w=element.w,
                    h=element.h
                ),
                content=content
            ))
            
        return layers

    def _map_type(self, layout_type: str) -> str:
        mapping = {
            "heading": "text",
            "text": "text",
            "image": "image",
            "table": "table",
            "figure": "figure"
        }
        return mapping.get(layout_type, "shape")

    def _find_text_for_box(self, element, ocr: OCRResult) -> str:
        # Simple overlap logic (placeholder)
        matched_lines = []
        for line in ocr.lines:
            if self._is_inside(line, element):
                matched_lines.append(line.text)
        return " ".join(matched_lines)

    def _is_inside(self, inner, outer) -> bool:
        return (inner.x >= outer.x and 
                inner.y >= outer.y and 
                (inner.x + inner.w) <= (outer.x + outer.w) and 
                (inner.y + inner.h) <= (outer.y + outer.h))

document_builder_service = DocumentBuilderService()
