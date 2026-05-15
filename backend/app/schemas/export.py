from pydantic import BaseModel

class ExportRequest(BaseModel):
    project_id: str

class ExportResponse(BaseModel):
    download_url: str
