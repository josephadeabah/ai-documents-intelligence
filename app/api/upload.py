
# =========================
# 10. API Routes
# =========================

# app/api/upload.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import shutil
import uuid
from pathlib import Path

from app.core.database import get_db
from app.services.document_service import document_service
from app.services.pdf_loader import validate_file, extract_metadata
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.core.logging import app_logger
from app.core.config import settings

router = APIRouter(prefix="/upload", tags=["Upload"])

# Create temp directory if not exists
TEMP_DIR = Path("/tmp/rag_uploads")
TEMP_DIR.mkdir(exist_ok=True)

@router.post("/", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document for processing
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Save temporarily
    temp_file_path = TEMP_DIR / f"{uuid.uuid4()}_{file.filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate file
        validate_file(str(temp_file_path), settings.MAX_FILE_SIZE_MB)
        
        # Extract metadata
        metadata = extract_metadata(str(temp_file_path))
        
        # Create document record
        document = await document_service.create_document(
            db=db,
            filename=file.filename,
            file_path=str(temp_file_path),
            metadata=metadata
        )
        
        # Process in background
        background_tasks.add_task(document_service.process_document, db, document.id)
        
        app_logger.info(f"Document uploaded: {file.filename} (ID: {document.id})")
        
        return document
        
    except Exception as e:
        # Clean up on error
        if temp_file_path.exists():
            temp_file_path.unlink()
        
        app_logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[DocumentResponse])
async def upload_multiple_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload multiple PDF documents
    """
    documents = []
    
    for file in files:
        # Validate extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            continue
        
        temp_file_path = TEMP_DIR / f"{uuid.uuid4()}_{file.filename}"
        
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            validate_file(str(temp_file_path), settings.MAX_FILE_SIZE_MB)
            metadata = extract_metadata(str(temp_file_path))
            
            document = await document_service.create_document(
                db=db,
                filename=file.filename,
                file_path=str(temp_file_path),
                metadata=metadata
            )
            
            background_tasks.add_task(document_service.process_document, db, document.id)
            documents.append(document)
            
        except Exception as e:
            app_logger.error(f"Failed to upload {file.filename}: {str(e)}")
            continue
    
    return documents