from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import logging
import os

# Load .env
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Gemini
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")

    # Database
    SQLALCHEMY_DATABASE_URL: str = os.getenv(
        "SQLALCHEMY_DATABASE_URL",
        "sqlite+aiosqlite:///./editable_image.db"
    )

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    class Config:
        env_file = ".env"

settings = Settings()

logger.info(f"GOOGLE_API_KEY FOUND: {bool(settings.GOOGLE_API_KEY)}")
logger.info(f"DATABASE URL: {settings.SQLALCHEMY_DATABASE_URL}")