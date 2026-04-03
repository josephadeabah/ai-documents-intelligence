# app/api/query.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services.rag_pipeline import rag_pipeline
from app.schemas.query import QueryRequest, QueryResponse, QueryHistoryResponse
from app.models.document import QueryLog
from app.core.logging import app_logger

router = APIRouter(prefix="/query", tags=["Query"])

@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query documents using RAG
    """
    try:
        result = await rag_pipeline.answer_query(
            db=db,
            query=request.query,
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            document_ids=request.document_ids
        )
        
        app_logger.info(f"Query processed: '{request.query[:50]}...' in {result['response_time_ms']:.2f}ms")
        return QueryResponse(**result)
        
    except Exception as e:
        app_logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def query_documents_stream(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Stream query response token by token
    """
    async def event_stream():
        async for chunk in rag_pipeline.stream_answer(
            db=db,
            query=request.query,
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            document_ids=request.document_ids
        ):
            yield chunk
    
    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson"
    )

@router.get("/history", response_model=List[QueryHistoryResponse])
async def get_query_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent query history
    """
    queries = db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit).all()
    return queries