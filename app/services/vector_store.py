# 8. app/services/vector_store.py
# =========================
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import numpy as np
from app.models.document import Chunk, Document
from app.core.database import get_db_context
from app.core.logging import app_logger
from app.core.config import settings

class VectorStore:
    """PostgreSQL pgvector-based vector store"""
    
    def __init__(self):
        self.dimension = settings.EMBEDDING_DIM
    
    async def add_embeddings(
        self, 
        db: Session, 
        document_id: int, 
        chunks: List[Dict[str, Any]], 
        embeddings: np.ndarray
    ) -> List[Chunk]:
        """Store embeddings in database"""
        chunk_objects = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_obj = Chunk(
                document_id=document_id,
                chunk_index=chunk["index"],
                chunk_text=chunk["text"],
                embedding=embedding.tolist(),
                char_count=chunk.get("char_count"),
                token_count=chunk.get("token_count")
            )
            db.add(chunk_obj)
            chunk_objects.append(chunk_obj)
        
        db.commit()
        app_logger.info(f"Stored {len(chunk_objects)} embeddings for document {document_id}")
        
        return chunk_objects
    
    async def similarity_search(
        self,
        db: Session,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity"""
        
        # Build query with optional document filtering
        query = db.query(
            Chunk,
            Document.filename.label("document_name"),
            Chunk.embedding.cosine_distance(query_embedding.tolist()).label("similarity")
        ).join(Document, Chunk.document_id == Document.id)
        
        if document_ids:
            query = query.filter(Chunk.document_id.in_(document_ids))
        
        # Order by similarity (lower distance = more similar)
        results = query.order_by(
            Chunk.embedding.cosine_distance(query_embedding.tolist())
        ).limit(top_k).all()
        
        formatted_results = []
        for chunk, doc_name, similarity in results:
            formatted_results.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": doc_name,
                "chunk_index": chunk.chunk_index,
                "text": chunk.chunk_text,
                "similarity_score": 1 - float(similarity)  # Convert distance to similarity
            })
        
        app_logger.debug(f"Found {len(formatted_results)} similar chunks")
        return formatted_results
    
    async def delete_document_embeddings(self, db: Session, document_id: int) -> int:
        """Delete all embeddings for a document"""
        deleted = db.query(Chunk).filter(Chunk.document_id == document_id).delete()
        db.commit()
        app_logger.info(f"Deleted {deleted} embeddings for document {document_id}")
        return deleted

# Singleton instance
vector_store = VectorStore()