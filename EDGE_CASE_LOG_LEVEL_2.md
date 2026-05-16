# Level 2 Edge Case Log - EditableImage

This log documents edge cases specifically related to the Level 2 additive graphics pipeline (icons, logos, device mockups).

## Encountered & Handled Edge Cases

### 1. Level 2 Graphic Overlapping with Level 1 Text/Table
- **Description**: A detected icon or logo bounding box overlaps with an existing Level 1 text or table element.
- **Handling**: The Level 2 element is automatically skipped to prioritize Level 1 integrity. A `SkippedElement` entry is created with the reason "overlaps with Level 1 element".
- **Status**: Handled in `PipelineService`.

### 2. Device Mockup with Internal Text
- **Description**: A computer or phone mockup contains text that might have been partially extracted by Level 1.
- **Handling**: Level 1 extracts the text as editable. Level 2 extracts the whole device as an image layer. The overlap check prevents the image layer from obscuring the editable text if they overlap significantly.
- **Status**: Handled by L1 priority.

### 4. Image Preview Not Loading
- **Description**: Image layers appear empty in the editor preview due to CORS or loading latency.
- **Handling**: Added a fallback UI (dashed rectangle with light fill) to indicate where the image is. Added `anonymous` cross-origin support and robust URL encoding.
- **Status**: Handled.

### 5. Graphics Cut Off in PPTX
- **Description**: Imprecise bounding boxes from AI result in icons or logos being partially cropped.
- **Handling**: Implemented "Safety Padding" (5%) in the `PPTXService` crop logic and updated Gemini prompts to request generous bounding boxes.
- **Status**: Handled.

## Unresolved Issues (Future Improvement Needed)

### 1. Vector Reconstruction for Icons
- **Description**: Icons are currently flat images. They cannot be color-changed or resized without loss of quality.
- **Current Status**: Not handled. Future pass could use a vectorizer.

### 2. Blurry Icon Detection
- **Description**: Very small or blurry icons might be missed by Gemini or flagged with low confidence.
- **Current Status**: Logged as skipped if the AI is uncertain.

### 3. Z-Index Conflicts
- **Description**: Determining if a graphic should be behind or in front of text when they are very close but not overlapping.
- **Current Status**: All Level 2 graphics are currently added as layers after Level 1 elements (visually "on top" if they were to overlap, but overlap is forbidden).
