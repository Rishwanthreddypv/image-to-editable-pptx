import google.generativeai as genai
import json
from PIL import Image
from app.core.config import settings, logger
from app.schemas.layer import Layer, GeometryBase

class GeminiVisionService:
    def __init__(self):
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            # Try to find the best available model
            self.model_name = self._get_best_model()
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Using Gemini model: {self.model_name}")
        else:
            self.model = None

    def _get_best_model(self):
        try:
            # List available models to see what this API key supports
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Prefer 1.5 flash variants
            for m in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-1.5-pro"]:
                if m in models:
                    return m
            
            # Fallback to whatever is available
            if models:
                return models[0]
        except Exception as e:
            logger.warning(f"Could not list models: {e}. Defaulting to gemini-1.5-flash")
        
        return 'gemini-1.5-flash'

    async def analyze_image(self, image_path: str):
        if not self.model:
            logger.warning("Google API Key not set. Falling back to mock mode.")
            return None

        try:
            img = Image.open(image_path)
            
            prompt = """
            Analyze this image and extract all editable elements into a structured JSON format. 

            1. EXTRACTION RULES:
               - TEXT: Identify headings and paragraphs. Extract each as a separate 'text' layer.
               - TABLES: If you see data clearly arranged in a grid (even if borders are invisible), extract it as a SINGLE 'table' layer. 
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

            response = self.model.generate_content([prompt, img])
            
            # Clean up response text in case Gemini adds markdown blocks
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()

            data = json.loads(text_response)
            
            # Robust parsing
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
                    id=f"gemini_{i}",
                    type=item['type'],
                    geometry=GeometryBase(**geometry),
                    content=content,
                    style=item.get('style', {})
                ))

            return layers, metadata, skipped_data
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                logger.error(f"Gemini API Quota Exceeded: {str(e)}")
            else:
                logger.error(f"Gemini analysis failed: {str(e)}")
            return None

    async def analyze_graphics(self, image_path: str):
        """
        Level 2 Pass: Detect icons, logos, device mockups, and small graphical elements.
        """
        if not self.model:
            return None

        try:
            img = Image.open(image_path)
            
            prompt = """
            Analyze this image specifically for non-text graphical elements.
            
            1. TARGET ELEMENTS:
               - Icons & Logos: Detect every icon, symbol, or brand mark. 
                 IMPORTANT: Extract the entire logical icon as a SINGLE unit. DO NOT split complex icons into multiple layers.
               - Device Mockups: Extract computers, tablets, phones, or any hardware frames.
               - Decorative Graphics: Extract shapes, arrows, dots, patterns, and flourishes.
            
            2. EXCLUSION RULES:
               - DO NOT extract text paragraphs or headings. These are already handled.
               - Only focus on the graphical/pictorial components.
            
            3. GEOMETRY:
               - Provide 'x', 'y', 'w', 'h' for every graphic relative to a 1280x720 coordinate system.
            
            4. CLASSIFICATION:
               - Use 'type': 'image' for all these elements.
               - In 'content', include a 'label' (e.g., 'logo', 'icon', 'monitor', 'decorative_dots').

            OUTPUT FORMAT:
            {
              "graphics": [
                {
                  "type": "image",
                  "label": "company_logo_icon",
                  "geometry": {"x": 50, "y": 50, "w": 30, "h": 30}
                }
              ],
              "skipped_graphics": []
            }
            
            Return ONLY the raw JSON.
            """

            response = self.model.generate_content([prompt, img])
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()

            data = json.loads(text_response)
            graphics_data = data.get('graphics', [])
            skipped_data = data.get('skipped_graphics', [])

            layers = []
            for i, item in enumerate(graphics_data):
                geom_raw = item.get('geometry', {})
                # Apply a standard 5% padding to the detection at the source
                # to ensure all future crops and previews are consistent.
                orig_x = geom_raw.get('x', 0)
                orig_y = geom_raw.get('y', 0)
                orig_w = geom_raw.get('w', 0)
                orig_h = geom_raw.get('h', 0)
                
                padding = 0.05
                px = orig_x - (orig_w * padding)
                py = orig_y - (orig_h * padding)
                pw = orig_w * (1 + 2 * padding)
                ph = orig_h * (1 + 2 * padding)

                layers.append(Layer(
                    id=f"gemini_gfx_{i}",
                    type="image",
                    geometry=GeometryBase(x=max(0, px), y=max(0, py), w=pw, h=ph),
                    content={
                        "label": item.get('label', 'graphic'),
                        "original_image": image_path,
                        "raw_geometry": {"x": orig_x, "y": orig_y, "w": orig_w, "h": orig_h}
                    }
                ))

            return layers, skipped_data
        except Exception as e:
            logger.error(f"Gemini graphics analysis failed: {str(e)}")
            return [], []

gemini_service = GeminiVisionService()
