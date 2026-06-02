from dotenv import load_dotenv
from pathlib import Path
import os
import logging

# External secure env path
env_path = Path(r"C:\secure_configs\.env")

# Load environment variables
loaded = load_dotenv(dotenv_path=env_path)

if not loaded:
    raise FileNotFoundError(f"Could not load .env from: {env_path}")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


class Settings:
    PROJECT_NAME: str = "EditableImage"
    UPLOAD_DIR: str = "backend/uploads"
    SQLALCHEMY_DATABASE_URL: str = "sqlite+aiosqlite:///./editable_image.db"


settings = Settings()

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

# OCR
AZURE_OCR_ENDPOINT = os.getenv("AZURE_OCR_ENDPOINT")
AZURE_OCR_API_KEY = os.getenv("AZURE_OCR_API_KEY")

# Embeddings
AZURE_EMBEDDING_ENDPOINT = os.getenv("AZURE_EMBEDDING_ENDPOINT")
AZURE_EMBEDDING_API_KEY = os.getenv("AZURE_EMBEDDING_API_KEY")

# Optional feature flag
ENABLE_GRAPH_EXTRACTION = os.getenv("ENABLE_GRAPH_EXTRACTION", "true").lower() == "true"

# Basic validation
required_vars = {
    "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
    "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
    "AZURE_OCR_ENDPOINT": AZURE_OCR_ENDPOINT,
    "AZURE_OCR_API_KEY": AZURE_OCR_API_KEY,
    "AZURE_EMBEDDING_ENDPOINT": AZURE_EMBEDDING_ENDPOINT,
    "AZURE_EMBEDDING_API_KEY": AZURE_EMBEDDING_API_KEY,
}

print("API key loaded:", bool(AZURE_OPENAI_API_KEY))
print("Endpoint loaded:", bool(AZURE_OPENAI_ENDPOINT))

missing = [name for name, value in required_vars.items() if not value]

if missing:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing)}"
    )