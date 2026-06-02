import base64
import json
import os
from PIL import Image
from openai import AzureOpenAI
from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    logger
)
from app.schemas.layer import Layer, GeometryBase

class AzureVisionService:
    def __init__(self):
        if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
            self.client = AzureOpenAI(
                api_key=AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview", # Standard version for vision
                azure_endpoint=AZURE_OPENAI_ENDPOINT
            )
            # Default deployment name - usually gpt-4o or gpt-4-vision
            self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            logger.info(f"Using Azure OpenAI deployment: {self.deployment_name}")
        else:
            self.client = None
            logger.warning("Azure OpenAI credentials not fully set.")

    def _encode_image(self, image_path: str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def analyze_image(self, image_path: str):
        if not self.client:
            logger.warning("Azure OpenAI client not initialized. Falling back.")
            return None

        try:
            base64_image = self._encode_image(image_path)
            
            prompt = """
            Analyze this image and extract all editable elements into a structured JSON format. 

            1. EXTRACTION RULES:
               - TEXT: Identify headings and paragraphs. Extract each as a separate 'text' layer.
               - TABLES: If you see data clearly arranged in a grid (even if borders are invisible), extract it as a SINGLE 'table' layer. 
               - SEMANTIC ROLE: For each layer, assign a 'semantic_role':
                 - 'HEADING': For titles.
                 - 'PARAGRAPH': For body text.
                 - 'DATA_CELL': For values inside a table.
                 - 'NODE_LABEL': For labels identifying parts of a diagram (e.g. "Database", "Functions").
                 - 'UI_LABEL': For text that is part of the application interface (e.g. "File", "Edit").
                 A table's content MUST have a 'cells' array:
                 - Each cell: {"rowIndex": 0, "colIndex": 0, "content": "cell text"}
               - DO NOT merge simple headers with trailing page numbers or unit numbers into a 'table'. Extract them as separate 'text' layers or a single 'text' layer if they are logical parts of the same line.
               - TYPOGRAPHY: For EVERY text layer, extract exact styles:
                 - 'style': {'fontSize': px, 'color': HEX, 'fontFamily': string, 'fontWeight': 'bold'|'normal', 'align': 'left'|'center'|'right'}
            
            2. GEOMETRY:
               - Provide 'x', 'y', 'w', 'h' for every layer relative to a 1280x720 coordinate system.
               - For a table, 'geometry' should be the bounding box of the ENTIRE table.
            
            3. METADATA:
               - HEX background color in 'background_hex'.
               - 'total_elements_observed': Count major logical blocks (a table counts as 1).

            OUTPUT FORMAT EXAMPLE:
            {
              "layers": [
                {
                  "type": "table",
                  "content": {
                    "cells": [
                      {"rowIndex": 0, "colIndex": 0, "content": "Item"},
                      {"rowIndex": 0, "colIndex": 1, "content": "Price"},
                      {"rowIndex": 1, "colIndex": 0, "content": "Apple"},
                      {"rowIndex": 1, "colIndex": 1, "content": "$1.00"}
                    ]
                  },
                  "geometry": {"x": 100, "y": 200, "w": 300, "h": 150}
                }
              ],
              "metadata": {
                "background_hex": "#FFFFFF",
                "total_elements_observed": 1
              }
            }
            
            Return ONLY raw JSON.
            """

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            text_response = response.choices[0].message.content.strip()
            data = json.loads(text_response)
            
            # Robust parsing (matching gemini_service logic)
            if isinstance(data, list):
                layers_data = data
                skipped_data = []
                metadata = {}
            else:
                layers_data = data.get('layers', [])
                skipped_data = data.get('skipped_elements', [])
                metadata = data.get('metadata', {})

            layers = []
            for i, item in enumerate(layers_data):
                content = item.get('content', {})
                if isinstance(content, str):
                    content = {"text": content}

                geom_raw = item.get('geometry', {})
                geometry = {
                    'x': geom_raw.get('x', 0),
                    'y': geom_raw.get('y', 0),
                    'w': geom_raw.get('w') if 'w' in geom_raw else geom_raw.get('width', 0),
                    'h': geom_raw.get('h') if 'h' in geom_raw else geom_raw.get('height', 0)
                }

                layers.append(Layer(
                    id=f"azure_{i}",
                    type=item['type'],
                    geometry=GeometryBase(**geometry),
                    content=content,
                    style=item.get('style', {})
                ))

            return layers, metadata, skipped_data
        except Exception as e:
            logger.error(f"Azure analysis failed: {str(e)}")
            return None

    async def analyze_graphics(self, image_path: str):
        if not self.client:
            return None, []

        try:
            base64_image = self._encode_image(image_path)
            
            prompt = """
            Analyze this image specifically for non-text graphical elements and structural organization.
            
            1. TARGET ELEMENTS:
               - Icons & Logos: Detect every icon, symbol, or brand mark. 
                 IMPORTANT: Extract the entire logical icon as a SINGLE unit. DO NOT split complex icons into multiple layers.
               - Device Mockups: Extract computers, tablets, phones, or any hardware frames.
               - Decorative Graphics: Extract shapes, arrows, dots, patterns, and flourishes.
            
            2. LAYOUT & CONTAINERS:
               - Identify major logical containers and structural regions.
               - Types: 'panel' (sidebars/nav), 'toolbar', 'card' (boxes with content), 'workspace' (main area), 'group' (generic clustering).
               - Provide bounding boxes for these containers.
            
            3. EXCLUSION RULES:
               - DO NOT extract text paragraphs or headings. These are already handled.
               - Only focus on the graphical/pictorial components and structural containers.
            
            4. GEOMETRY:
               - Provide 'x', 'y', 'w', 'h' for every element relative to a 1280x720 coordinate system.
            
            5. CLASSIFICATION & SEMANTIC ROLES:
               - Use 'type': 'image' for graphics.
               - Use 'type': 'container' for structural regions.
               - In 'content', include:
                 - 'label': (e.g., 'logo', 'icon', 'sidebar', 'user_card', 'nav_bar', 'workspace_area')
                 - 'confidence': (float 0.0-1.0)
                 - 'semantic_role': ONE OF ['STRUCTURAL_CONTAINER', 'CONTENT_NODE', 'TABLE', 'TEXT_GROUP', 'ICON_GROUP', 'CONNECTOR', 'UI_CHROME', 'DECORATIVE']
                 - 'is_structural': (boolean, true if it's a main layout block, false if it's UI chrome or decorative)

            ROLE DEFINITIONS:
            - STRUCTURAL_CONTAINER: Large regions organizing the layout (panels, cards, workspace).
            - CONTENT_NODE: Atomic logical entities (e.g., an architecture node like "Kubernetes" or "Database").
            - UI_CHROME: Navigation bars, toolbars, buttons belonging to the app interface, NOT the diagram/document content.
            - TABLE: Only for actual data grids with row/column structure.

            OUTPUT FORMAT:
            {
              "graphics": [
                {
                  "type": "image",
                  "label": "company_logo_icon",
                  "geometry": {"x": 50, "y": 50, "w": 30, "h": 30},
                  "confidence": 0.95,
                  "semantic_role": "CONTENT_NODE"
                }
              ],
              "containers": [
                {
                  "type": "container",
                  "label": "side_panel",
                  "geometry": {"x": 0, "y": 0, "w": 200, "h": 720},
                  "confidence": 0.9,
                  "semantic_role": "UI_CHROME",
                  "is_structural": false
                }
              ],
              "skipped_graphics": []
            }
            
            Return ONLY raw JSON.
            """

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                # Using JSON mode for flexibility, though newer models support strict schema
                response_format={"type": "json_object"}
            )
            
            text_response = response.choices[0].message.content.strip()
            data = json.loads(text_response)
            graphics_data = data.get('graphics', [])
            containers_data = data.get('containers', [])
            skipped_data = data.get('skipped_graphics', [])

            layers = []
            
            # Process graphics
            for i, item in enumerate(graphics_data):
                geom_raw = item.get('geometry', {})
                geometry = {
                    'x': geom_raw.get('x', 0),
                    'y': geom_raw.get('y', 0),
                    'w': geom_raw.get('w', 0),
                    'h': geom_raw.get('h', 0)
                }

                layers.append(Layer(
                    id=f"azure_gfx_{i}",
                    type="image",
                    geometry=GeometryBase(**geometry),
                    content={
                        "label": item.get('label', 'graphic'),
                        "original_image": image_path,
                        "confidence": item.get('confidence', 0.8),
                        "semantic_role": item.get('semantic_role', 'CONTENT_NODE')
                    }
                ))
            
            # Process containers
            for i, item in enumerate(containers_data):
                geom_raw = item.get('geometry', {})
                layers.append(Layer(
                    id=f"azure_cont_{i}",
                    type="container",
                    geometry=GeometryBase(**geom_raw),
                    content={
                        "label": item.get('label', 'container'),
                        "container_type": item.get('label', 'generic'),
                        "confidence": item.get('confidence', 0.7),
                        "semantic_role": item.get('semantic_role', 'STRUCTURAL_CONTAINER'),
                        "is_structural": item.get('is_structural', True)
                    }
                ))

            return layers, skipped_data
        except Exception as e:
            logger.error(f"Azure graphics analysis failed: {str(e)}")
            return [], []

    async def analyze_nested_containers(self, image_path: str, parent_id: str, parent_geometry: GeometryBase):
        if not self.client:
            return []

        try:
            base64_image = self._encode_image(image_path)
            
            prompt = f"""
            Analyze the specified region of this image (x: {parent_geometry.x}, y: {parent_geometry.y}, w: {parent_geometry.w}, h: {parent_geometry.h}) 
            for nested structural containers.
            
            1. TARGET NESTED ELEMENTS:
               - Inner cards, sub-panels, nested boxes, or grouped sections strictly WITHIN the parent region.
               - Types: 'card', 'sub_panel', 'inner_box', 'group'.
            
            2. GEOMETRY:
               - Provide 'x', 'y', 'w', 'h' for every nested element relative to the same 1280x720 coordinate system.
               - Ensure they are logically contained within the parent bbox.
            
            3. OUTPUT FORMAT:
            {{
              "nested_containers": [
                {{
                  "type": "container",
                  "label": "inner_card",
                  "geometry": {{"x": 250, "y": 150, "w": 100, "h": 100}}
                }}
              ]
            }}
            
            Return ONLY raw JSON.
            """

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            text_response = response.choices[0].message.content.strip()
            data = json.loads(text_response)
            nested_data = data.get('nested_containers', [])

            nested_layers = []
            for i, item in enumerate(nested_data):
                geom_raw = item.get('geometry', {})
                nested_layers.append(Layer(
                    id=f"{parent_id}_nested_{i}",
                    type="container",
                    geometry=GeometryBase(**geom_raw),
                    content={
                        "label": item.get('label', 'nested_container'),
                        "container_type": item.get('label', 'generic'),
                        "parent_id": parent_id
                    }
                ))

            return nested_layers
        except Exception as e:
            logger.error(f"Azure nested analysis failed: {str(e)}")
            return []

azure_vision_service = AzureVisionService()
