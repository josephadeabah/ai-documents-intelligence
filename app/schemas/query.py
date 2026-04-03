from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(5, ge=1, le=20)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(500, ge=50, le=2000)
    document_ids: Optional[List[int]] = Field(None, description="Filter by specific documents")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()

class ContextChunk(BaseModel):
    id: int
    document_id: int
    document_name: str
    chunk_index: int
    text: str
    similarity_score: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[ContextChunk]
    total_tokens: Optional[int]
    response_time_ms: float
    model_used: str
    
class StreamingChunk(BaseModel):
    type: str  # "answer", "source", "done", "error"
    content: str
    metadata: Optional[Dict[str, Any]] = None

class QueryHistoryResponse(BaseModel):
    id: int
    query_text: str
    response_text: str
    response_time_ms: float
    created_at: datetime