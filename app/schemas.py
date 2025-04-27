from pydantic import BaseModel
from typing import List

class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    task_id: str
    message: str

class WordInfo(BaseModel):
    """Model for word information with TF and IDF metrics."""
    word: str
    tf: int
    idf: float

class ResultsResponse(BaseModel):
    """Response model for results endpoint with pagination info."""
    items: List[WordInfo]
    total: int
    page: int
    pages: int 