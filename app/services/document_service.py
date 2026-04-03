from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
import os
import shutil
from datetime import datetime
from pathlib import Path

from app.models.document import Document, Chunk
from app.schemas.document import DocumentFilter, DocumentStatus
from app.services.pdf_loader import extract_text, extract_metadata, validate_file
from app.services.chunking import chunk_text
from app.services.embedding import embed_text
from app.services.vector_store import vector_store
from app.core.logging import app_logger
from app.core.exceptions import DocumentProcessingError, DocumentNotFoundError

class DocumentService:
    """Service for managing documents"""
    
    @staticmethod
    async def create_document(
        db: Session,
        filename: str,
        file_path: str,
        metadata: Dict[str, Any]
    ) -> Document:
        """Create document record"""
        document = Document(
            filename=filename,
            file_path=file_path,
            file_size=metadata.get("file_size"),
            file_type="pdf",
            title=metadata.get("title"),
            author=metadata.get("author"),
            page_count=metadata.get("page_count"),
            status=DocumentStatus.PENDING
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    async def process_document(db: Session, document_id: int) -> Document:
        """Process document: extract text, chunk, embed"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise DocumentNotFoundError(document_id)
        
        try:
            # Update status
            document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # Extract text from PDF
            text = extract_text(document.file_path)
            
            # Chunk text
            chunks = chunk_text(text, {"document_id": document_id})
            
            if not chunks:
                raise DocumentProcessingError(document_id, "No chunks generated")
            
            # Generate embeddings
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await embed_text(chunk_texts)
            
            # Store in vector database
            await vector_store.add_embeddings(db, document_id, chunks, embeddings)
            
            # Update document status
            document.status = DocumentStatus.COMPLETED
            db.commit()
            
            app_logger.info(f"Successfully processed document {document_id}")
            return document
            
        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            db.commit()
            app_logger.error(f"Failed to process document {document_id}: {str(e)}")
            raise DocumentProcessingError(document_id, str(e))
    
    @staticmethod
    async def get_document(db: Session, document_id: int) -> Document:
        """Get document by ID"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise DocumentNotFoundError(document_id)
        return document
    
    @staticmethod
    async def get_documents(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[DocumentFilter] = None
    ) -> tuple[List[Document], int]:
        """Get documents with filtering"""
        query = db.query(Document)
        
        if filters:
            if filters.status:
                query = query.filter(Document.status == filters.status)
            if filters.filename_contains:
                query = query.filter(Document.filename.contains(filters.filename_contains))
            if filters.from_date:
                query = query.filter(Document.created_at >= filters.from_date)
            if filters.to_date:
                query = query.filter(Document.created_at <= filters.to_date)
        
        total = query.count()
        documents = query.offset(skip).limit(limit).all()
        
        return documents, total
    
    @staticmethod
    async def delete_document(db: Session, document_id: int) -> bool:
        """Delete document and associated chunks"""
        document = await DocumentService.get_document(db, document_id)
        
        # Delete embeddings from vector store
        await vector_store.delete_document_embeddings(db, document_id)
        
        # Delete physical file
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        app_logger.info(f"Deleted document {document_id}")
        return True
    
    @staticmethod
    async def get_document_stats(db: Session, document_id: int) -> Dict[str, Any]:
        """Get statistics for a document"""
        document = await DocumentService.get_document(db, document_id)
        
        chunks_count = db.query(Chunk).filter(Chunk.document_id == document_id).count()
        total_chars = db.query(Chunk).filter(Chunk.document_id == document_id).with_entities(
            db.func.sum(Chunk.char_count)
        ).scalar() or 0
        
        return {
            "document_id": document_id,
            "filename": document.filename,
            "chunks_count": chunks_count,
            "total_chars": total_chars,
            "status": document.status,
            "created_at": document.created_at
        }

# Singleton instance
document_service = DocumentService()