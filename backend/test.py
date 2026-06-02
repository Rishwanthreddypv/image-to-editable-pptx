from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT
)

print("Loaded key:", bool(AZURE_OPENAI_API_KEY))
print("Loaded endpoint:", bool(AZURE_OPENAI_ENDPOINT))