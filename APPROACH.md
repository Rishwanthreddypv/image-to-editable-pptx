# Technical Approach - EditableImage

## Architecture Overview
The system uses a **Vision-to-Layout** pipeline that leverages Large Multimodal Models (LMMs) to bypass traditional OCR-heavy heuristics, directly converting images into structured editable layers.

## Core Technologies
- **AI Engine**: Azure OpenAI (GPT-4o).
- **Backend**: FastAPI (Python), OpenCV, `python-pptx`.
- **Frontend**: Next.js, Konva.js (16:9 interactive canvas).

## Pipeline Structure
1. **Preprocessing**: Deskewing and normalization.
2. **Vision Analysis**: Single-pass extraction of layers and metadata at 1280x720.
3. **Fidelity Scoring**: Calculated by comparing AI-observed vs. successfully parsed elements.
4. **Validation**: Flags low-resolution inputs and handles solid backgrounds.

## Known Limitations & Future Improvements
- **Paragraph Overlap (High Priority)**: Currently, multi-paragraph and low-res images often result in overlapping text blocks. Next versions will implement a layout collision-detection algorithm to ensure non-overlapping, well-spaced paragraphs.
- **Style Detection**: Improving detection of font styles and colors.
- **Cell Bounding Boxes**: For pixel-perfect table alignment.
- **Vectorization**: Converting figures into native PowerPoint shapes.
