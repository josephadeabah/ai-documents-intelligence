# =========================
# 5. app/services/pdf_loader.py
# =========================
from PyPDF2 import PdfReader
from typing import Dict, Any, List
import os
from pathlib import Path
from app.core.exceptions import InvalidFileError, DocumentProcessingError
from app.core.logging import app_logger
import magic

class PDFLoader:
    """Advanced PDF loader with metadata extraction"""
    
    @staticmethod
    def validate_file(file_path: str, max_size_mb: int = 10) -> None:
        """Validate file before processing"""
        file_size = os.path.getsize(file_path)
        if file_size > max_size_mb * 1024 * 1024:
            raise InvalidFileError(f"File size exceeds {max_size_mb}MB limit")
        
        # Check if it's a valid PDF
        mime = magic.from_file(file_path, mime=True)
        if mime != "application/pdf":
            raise InvalidFileError(f"Invalid file type. Expected PDF, got {mime}")
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from PDF with error handling"""
        try:
            reader = PdfReader(file_path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num}]\n{page_text}\n")
                else:
                    app_logger.warning(f"No text found on page {page_num} of {file_path}")
            
            full_text = "\n".join(text_parts)
            
            if not full_text.strip():
                raise DocumentProcessingError(0, "No text could be extracted from PDF")
            
            app_logger.info(f"Extracted {len(full_text)} characters from {file_path}")
            return full_text
            
        except Exception as e:
            app_logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise DocumentProcessingError(0, f"PDF extraction failed: {str(e)}")
    
    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        try:
            reader = PdfReader(file_path)
            metadata = reader.metadata or {}
            
            return {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "page_count": len(reader.pages),
                "file_size": os.path.getsize(file_path)
            }
        except Exception as e:
            app_logger.warning(f"Failed to extract metadata: {str(e)}")
            return {"page_count": 0, "file_size": os.path.getsize(file_path)}

# Singleton instance
pdf_loader = PDFLoader()
extract_text = pdf_loader.extract_text
extract_metadata = pdf_loader.extract_metadata
validate_file = pdf_loader.validate_file