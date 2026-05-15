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
               - TABLES (PRIORITY): Look for any data organized in rows and columns, with or without visible grid lines. 
                 - Extract these as 'table' type.
                 - You MUST extract EVERY individual cell.
                 - For each cell, specify 'rowIndex', 'colIndex', and 'content'.
               - FIGURES: Extract non-text visual elements as 'figure'.
            
            2. GEOMETRY:
               - Provide 'x', 'y', 'w', 'h' for every layer relative to a 1280x720 coordinate system.
            
            3. METADATA:
               - HEX background color in 'background_hex'.
               - Count ALL visual elements (count every table cell as 1) in 'total_elements_observed'.

            OUTPUT FORMAT:
            {
              "layers": [
                {
                  "type": "text",
                  "content": {"text": "paragraph content"},
                  "geometry": {"x": 0, "y": 0, "w": 100, "h": 50}
                },
                {
                  "type": "table",
                  "content": {
                    "cells": [
                      {"rowIndex": 0, "colIndex": 0, "content": "Cell A1"},
                      {"rowIndex": 0, "colIndex": 1, "content": "Cell B1"}
                    ]
                  },
                  "geometry": {"x": 200, "y": 200, "w": 400, "h": 200}
                }
              ],
              "skipped_elements": [],
              "metadata": {
                "background_hex": "#ffffff",
                "total_elements_observed": 10
              }
            }
            
            Return ONLY the raw JSON.
            """

            response = self.model.generate_content([prompt, img])
            
            # Clean up response text in case Gemini adds markdown blocks
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()

            data = json.loads(text_response)
            
            # Robust parsing: handle if Gemini returns a list instead of the requested object
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
                # Ensure content is a dictionary
                content = item.get('content', {})
                if isinstance(content, str):
                    content = {"text": content}

                # Handle geometry key variations (w/h vs width/height)
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
                    content=content
                ))

            return layers, metadata, skipped_data
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                logger.error(f"Gemini API Quota Exceeded: {str(e)}")
            else:
                logger.error(f"Gemini analysis failed: {str(e)}")
            return None

gemini_service = GeminiVisionService()
