from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
from app.core.logging import app_logger

class DocumentIntelligenceException(Exception):
    """Base exception for Document Intelligence"""
    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class DocumentNotFoundError(DocumentIntelligenceException):
    def __init__(self, document_id: int):
        super().__init__(
            message=f"Document with ID {document_id} not found",
            status_code=404,
            details={"document_id": document_id}
        )

class DocumentProcessingError(DocumentIntelligenceException):
    def __init__(self, document_id: int, error: str):
        super().__init__(
            message=f"Failed to process document {document_id}: {error}",
            status_code=500,
            details={"document_id": document_id, "error": error}
        )

class EmbeddingError(DocumentIntelligenceException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=500)

class RateLimitExceededError(DocumentIntelligenceException):
    def __init__(self):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429
        )

class InvalidFileError(DocumentIntelligenceException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)

async def exception_handler(request: Request, exc: DocumentIntelligenceException):
    """Global exception handler"""
    app_logger.error(
        f"Exception occurred: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )

def setup_exception_handlers(app):
    """Setup exception handlers for FastAPI app"""
    app.add_exception_handler(DocumentIntelligenceException, exception_handler)