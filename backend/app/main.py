from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.api.router import api_router
from app.core.database import init_db
from app.core.config import logger, settings

app = FastAPI(title="Editable Image to PPTX API")

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Serve static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    logger.info("Starting up backend...")
    await init_db()

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Image to PPTX API is running"}
