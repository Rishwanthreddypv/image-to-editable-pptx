from fastapi import APIRouter
from app.api.routes import upload, documents, export

api_router = APIRouter()

api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(documents.router, prefix="/document", tags=["documents"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
