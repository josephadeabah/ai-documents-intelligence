# =========================
# 4. app/models/document.py
# =========================
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Float
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import VECTOR
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.config import settings
import json

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    file_type = Column(String(50))
    s3_key = Column(String(500))
    
    # Metadata
    title = Column(String(500))
    author = Column(String(255))
    page_count = Column(Integer)
    
    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_document_filename', 'filename'),
        Index('idx_document_status', 'status'),
        Index('idx_document_created', 'created_at'),
    )

class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    
    # Vector embedding (PostgreSQL pgvector)
    embedding = Column(VECTOR(settings.EMBEDDING_DIM))
    
    # Metadata
    char_count = Column(Integer)
    token_count = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index('idx_chunk_document', 'document_id'),
        Index('idx_chunk_index', 'document_id', 'chunk_index'),
        # HNSW index for vector similarity search (PostgreSQL 14+)
        Index('idx_chunk_embedding_hnsw', embedding, postgresql_using='hnsw', 
              postgresql_with_parameters={'m': 16, 'ef_construction': 64}),
    )

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    context_chunks = Column(Text)  # JSON string of chunk IDs used
    response_time_ms = Column(Float)
    
    # Metrics
    tokens_used = Column(Integer)
    model_used = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_query_log_created', 'created_at'),
    )