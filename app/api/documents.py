from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.services.document_service import document_service
from app.schemas.document import (
    DocumentResponse, DocumentDetailResponse, 
    DocumentListResponse, DocumentFilter, DocumentStatus
)
from app.core.logging import app_logger

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[DocumentStatus] = None,
    filename_contains: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all documents with pagination and filtering
    """
    filters = DocumentFilter(
        status=status,
        filename_contains=filename_contains
    )
    
    documents, total = await document_service.get_documents(
        db=db,
        skip=skip,
        limit=limit,
        filters=filters
    )
    
    return DocumentListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        documents=documents
    )

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document details by ID
    """
    try:
        stats = await document_service.get_document_stats(db, document_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and its embeddings
    """
    try:
        await document_service.delete_document(db, document_id)
        return {"message": f"Document {document_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get chunks of a document
    """
    from app.models.document import Chunk
    
    document = await document_service.get_document(db, document_id)
    
    chunks = db.query(Chunk).filter(
        Chunk.document_id == document_id
    ).offset(skip).limit(limit).all()
    
    total = db.query(Chunk).filter(Chunk.document_id == document_id).count()
    
    return {
        "document_id": document_id,
        "filename": document.filename,
        "total_chunks": total,
        "chunks": chunks
    }