# Edge Case Log - EditableImage

This log documents the edge cases encountered during testing, their handling strategies, and any unresolved issues.

## Encountered & Handled Edge Cases

### 1. Slide with no detectable background pattern (L1)
- **Description**: Source images with solid backgrounds (pure white or black).
- **Handling**: Gemini metadata identifies the background. `PPTXService` applies a solid fill.
- **Status**: Handled.

### 2. Image input has very low resolution (L1)
- **Description**: Source images smaller than 1280x720 pixels.
- **Handling**: Flagged as `low_resolution_flag=True`. Confidence set to Medium/Low.
- **Status**: Handled (Detection/Communication).

## Unresolved Issues (Future Improvement Needed)

### 1. Overlapping Paragraphs (Multi-Paragraph & Low-Res)
- **Description**: In images with multiple paragraphs or low resolution, the AI often returns overlapping bounding boxes for text blocks.
- **Current Status**: **NOT HANDLED**. The system currently renders layers exactly where the AI detects them, which can result in text overlapping in the editor and the PPTX.
- **Future Improvement**: Implement a layout engine to prevent bounding box collisions and ensure proper vertical spacing.

### 2. Vector Graphics Extraction
- **Description**: Complex SVGs or logos are extracted as flat image placeholders.
- **Current Status**: Not handled.

### 3. Precision Table Alignment
- **Description**: Column widths are estimated; pixel-perfect alignment is not yet achieved.
- **Current Status**: Partially handled via coordinate scaling.
