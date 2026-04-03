from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    title: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=255)

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    file_size: Optional[int]
    file_type: Optional[str]
    page_count: Optional[int]
    status: DocumentStatus
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    chunks_count: Optional[int] = 0
    total_chars: Optional[int] = 0

class ChunkResponse(BaseModel):
    id: int
    chunk_index: int
    chunk_text: str
    char_count: Optional[int]
    document_id: int
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    documents: List[DocumentResponse]

class DocumentFilter(BaseModel):
    status: Optional[DocumentStatus] = None
    filename_contains: Optional[str] = Field(None, max_length=100)
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    @validator('to_date')
    def validate_dates(cls, v, values):
        if v and values.get('from_date') and v < values['from_date']:
            raise ValueError('to_date must be after from_date')
        return v