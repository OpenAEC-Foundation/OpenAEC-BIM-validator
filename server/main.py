"""
FastAPI Server for Server-Side IFC Rendering POC

This server provides endpoints for:
- IFC file uploads
- Server-side IFC processing (to be implemented in subtask 4.2)
- Serving processed geometry to browser clients

Run with: uvicorn server.main:app --reload --port 8000
Or from server directory: uvicorn main:app --reload --port 8000
"""

import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create FastAPI app with metadata for auto-docs
app = FastAPI(
    title="IFC Server-Side Rendering POC",
    description="Server-side IFC processing API for Phase 0 research validation",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for uploaded files
UPLOAD_DIR = Path(tempfile.gettempdir()) / "ifc_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Maximum file size (500MB for large file testing)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB in bytes

# Track uploaded files for cleanup and status
uploaded_files: dict[str, dict] = {}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "IFC Server-Side Rendering POC",
        "version": "0.1.0",
        "endpoints": {
            "upload": "/api/upload",
            "status": "/api/status/{file_id}",
            "docs": "/docs",
        },
    }


@app.get("/api/health")
async def health_check():
    """API health check"""
    return {
        "status": "ok",
        "upload_dir": str(UPLOAD_DIR),
        "upload_dir_exists": UPLOAD_DIR.exists(),
        "files_tracked": len(uploaded_files),
    }


@app.post("/api/upload")
async def upload_ifc(
    ifc_file: UploadFile = File(..., description="IFC file to process"),
):
    """
    Upload an IFC file for server-side processing.

    - Accepts IFC files up to 500MB
    - Saves file to temp directory
    - Returns file_id for status checking and processing

    Returns:
        JSONResponse with file_id, filename, size, and upload status
    """
    start_time = time.time()

    # Validate file extension
    if not ifc_file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    filename_lower = ifc_file.filename.lower()
    if not filename_lower.endswith(".ifc"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected .ifc file, got: {ifc_file.filename}",
        )

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Read file content
    try:
        content = await ifc_file.read()
        file_size = len(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Save file to temp directory
    safe_filename = f"{file_id}_{ifc_file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    upload_time = time.time() - start_time

    # Track uploaded file
    file_info = {
        "file_id": file_id,
        "original_filename": ifc_file.filename,
        "saved_filename": safe_filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "file_size_mb": round(file_size / 1024 / 1024, 2),
        "upload_time_ms": round(upload_time * 1000, 2),
        "status": "uploaded",
        "processing_status": "pending",
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    uploaded_files[file_id] = file_info

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "File uploaded successfully",
            "file_id": file_id,
            "filename": ifc_file.filename,
            "file_size": file_size,
            "file_size_mb": file_info["file_size_mb"],
            "upload_time_ms": file_info["upload_time_ms"],
            "status": "uploaded",
            "next_step": f"Process file with POST /api/process/{file_id}",
        },
    )


@app.get("/api/status/{file_id}")
async def get_file_status(file_id: str):
    """
    Get status of an uploaded file.

    Args:
        file_id: UUID of the uploaded file

    Returns:
        File information and processing status
    """
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    return uploaded_files[file_id]


@app.get("/api/files")
async def list_files():
    """
    List all uploaded files with their status.

    Returns:
        List of all tracked files
    """
    return {
        "count": len(uploaded_files),
        "files": list(uploaded_files.values()),
    }


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """
    Delete an uploaded file.

    Args:
        file_id: UUID of the file to delete
    """
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    file_info = uploaded_files[file_id]
    file_path = Path(file_info["file_path"])

    # Delete file from disk
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting file: {str(e)}"
            )

    # Remove from tracking
    del uploaded_files[file_id]

    return {"success": True, "message": f"File {file_id} deleted"}


@app.delete("/api/files")
async def cleanup_files():
    """
    Delete all uploaded files and clean up.
    Useful for testing and cleanup after benchmarks.
    """
    deleted_count = 0
    errors = []

    for file_id, file_info in list(uploaded_files.items()):
        file_path = Path(file_info["file_path"])
        try:
            if file_path.exists():
                file_path.unlink()
            del uploaded_files[file_id]
            deleted_count += 1
        except Exception as e:
            errors.append(f"{file_id}: {str(e)}")

    return {
        "success": len(errors) == 0,
        "deleted_count": deleted_count,
        "errors": errors if errors else None,
    }


# Placeholder for future processing endpoint (subtask 4.2)
@app.post("/api/process/{file_id}")
async def process_ifc(file_id: str):
    """
    Process an uploaded IFC file (placeholder for subtask 4.2).

    This endpoint will:
    - Convert IFC to optimized geometry format
    - Return processed data for browser rendering

    Currently returns a placeholder response.
    """
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    file_info = uploaded_files[file_id]

    return {
        "status": "not_implemented",
        "message": "IFC processing will be implemented in subtask 4.2",
        "file_id": file_id,
        "filename": file_info["original_filename"],
        "file_size_mb": file_info["file_size_mb"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
