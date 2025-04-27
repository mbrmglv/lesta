from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class AnalysisStatus(str, Enum):
    """Enumeration of possible analysis statuses."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    task_id: str = Field(
        ..., 
        description="Unique identifier for tracking the analysis task",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    message: str = Field(
        ..., 
        description="Status message about the file upload",
        example="File upload successful. Processing started."
    )
    
    class Config:
        schema_extra = {
            "description": "Response returned when a file is successfully uploaded for processing"
        }

class WordInfo(BaseModel):
    """Model for word information with TF and IDF metrics."""
    word: str = Field(
        ..., 
        description="The analyzed word",
        example="example"
    )
    tf: int = Field(
        ..., 
        description="Term Frequency - number of times the word appears in the document",
        example=5,
        ge=0
    )
    idf: float = Field(
        ..., 
        description="Inverse Document Frequency - measure of how important the word is",
        example=1.204,
        ge=0.0
    )
    
    class Config:
        schema_extra = {
            "description": "Information about a word's TF-IDF metrics"
        }

class ResultsResponse(BaseModel):
    """Response model for results endpoint with pagination info."""
    items: List[WordInfo] = Field(
        ..., 
        description="List of word analysis results for the current page"
    )
    total: int = Field(
        ..., 
        description="Total number of word results available",
        example=150,
        ge=0
    )
    page: int = Field(
        ..., 
        description="Current page number",
        example=1,
        ge=1
    )
    pages: int = Field(
        ..., 
        description="Total number of pages available",
        example=15,
        ge=0
    )
    
    class Config:
        schema_extra = {
            "description": "Paginated response containing word analysis results"
        }

class ErrorResponse(BaseModel):
    """Model for error responses."""
    detail: str = Field(
        ..., 
        description="Error message describing what went wrong",
        example="File too large"
    )
    
    class Config:
        schema_extra = {
            "description": "Error response returned when a request fails"
        } 