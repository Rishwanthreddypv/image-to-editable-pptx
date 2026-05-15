import pytest
from fastapi.testclient import TestClient
from app.main import app
import asyncio

client = TestClient(app)

def test_document_lifecycle():
    # 1. Upload to get project ID
    file_content = b"fake image content"
    res = client.post(
        "/api/v1/upload/",
        files={"file": ("test.png", file_content, "image/png")}
    )
    project_id = res.json()["project_id"]
    
    # 2. Check status
    res = client.get(f"/api/v1/document/{project_id}/status")
    assert res.status_code == 200
    assert "status" in res.json()
