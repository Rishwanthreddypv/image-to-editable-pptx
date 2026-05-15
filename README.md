# Editable Image to PPTX

A complete end-to-end application that converts images of documents (containing text, tables, and figures) into fully editable PowerPoint (PPTX) presentations.

## Architecture

This is a monorepo containing:

- **Frontend (`/frontend`)**: A Next.js 14 application providing a rich, interactive canvas editor. Features include:
  - React Konva for high-performance canvas rendering.
  - Zustand for robust, history-aware state management (Undo/Redo).
  - Tailwind CSS for a polished, responsive UI.
  - Interactive property panels for editing text, tables, and geometric properties.
- **Backend (`/backend`)**: A FastAPI application managing the processing pipeline. Features include:
  - OpenCV for image preprocessing (deskew, denoise, contrast).
  - Pluggable AI Service architectures for OCR and Layout Analysis.
  - Background task processing for asynchronous document generation.
  - `python-pptx` integration for native PowerPoint export.

## Application Flow

1. **Upload**: User uploads an image via the Next.js frontend.
2. **Background Processing**: FastAPI accepts the file and delegates it to a background worker.
3. **AI Pipeline**: The image is preprocessed, its layout is detected (bounding boxes for text, tables, images), and text is extracted via OCR.
4. **Document Model**: The extracted data is unified into a canonical JSON `DocumentLayer` model.
5. **Interactive Editor**: The frontend polls for completion, then renders the editable layers on a canvas. Users can tweak layout, edit text, and fix table grids.
6. **Export**: The user clicks "Export", and the backend translates the updated JSON model directly into native PowerPoint objects (Textboxes, Tables, Shapes), returning a downloadable `.pptx` file.

## Setup & Deployment

### Prerequisites
- Docker and Docker Compose

### Quickstart (Docker)

To run the entire stack locally:

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs

### Local Development (Manual)

If you prefer to run the services outside of Docker:

**1. Backend**
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

**2. Frontend**
```bash
pnpm install
pnpm --filter frontend dev
```

## Environment Variables
See `.env.example` in the root. The frontend uses `NEXT_PUBLIC_API_URL` to route requests to the FastAPI backend.
