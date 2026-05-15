# Skipped Elements Report Guide

The system generates a dynamic report for every processed image. This report identifies elements the AI saw but could not reconstruct.

## Where to find the report:
1.  **PPTX Download**: When you click "Export PPTX", the report is returned in the HTTP Response Header: `X-Skipped-Elements`.
2.  **API Response**: The `/api/v1/documents/{id}/status` endpoint returns a `skipped_elements` array in the JSON body.

## Sample Report Format:
```json
[
  {
    "type": "figure",
    "reason": "Unsupported complex geometry",
    "geometry": { "x": 100, "y": 200, "w": 50, "h": 50 }
  },
  {
    "type": "text",
    "reason": "Low confidence score / blurry source",
    "geometry": { "x": 400, "y": 50, "w": 120, "h": 30 }
  }
]
```

*Note: If the list is empty `[]`, it means all detected elements were successfully converted.*
