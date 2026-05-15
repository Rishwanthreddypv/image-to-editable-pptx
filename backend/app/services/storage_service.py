import os
import shutil
from fastapi import UploadFile
from app.core.config import settings

class StorageService:
    def __init__(self):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    async def save_upload(self, upload_file: UploadFile) -> str:
        file_path = os.path.join(settings.UPLOAD_DIR, upload_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return file_path

storage_service = StorageService()
