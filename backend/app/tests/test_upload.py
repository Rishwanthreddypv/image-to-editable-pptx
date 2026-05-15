import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_image():
    # Provide a tiny valid mock image
    file_content = b"fake image content"
    response = client.post(
        "/api/v1/upload/",
        files={"file": ("test.png", file_content, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert data["status"] == "processing"
