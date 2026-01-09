"""
FastAPI backend for IFC file validation web interface.

This server provides endpoints for:
- Health monitoring and observability
- IFC file uploads and validation
- Server-side IFC processing (converts IFC to optimized geometry)

Run with: uvicorn server.main:app --reload --port 8000
Or from server directory: uvicorn main:app --reload --port 8000
"""

import json
import logging
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from server.ids_validator import IDSValidator, ValidationReport, report_to_dict
from server.ifc_processor import GLTF_AVAILABLE, IFCProcessor
from server.job_manager import JobManager, JobStatusResponse
from server.models.validation_results import (
    ElementResult,
    RequirementResult,
    SeverityLevel,
    SpecificationResult,
    ValidationResult,
    ValidationStatus,
)
from ifc_validator.standards.resolver import get_bundled_ids


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        return json.dumps(log_data)


# Configure structured JSON logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.propagate = False

# Create FastAPI app with metadata for auto-docs
app = FastAPI(
    title="IFC Validation API",
    description="API for IFC file upload and validation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for uploaded files
UPLOAD_DIR = Path(tempfile.gettempdir()) / "ifc_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Maximum file size (500MB for large file testing)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB in bytes

# Maximum IDS file size (5MB)
MAX_IDS_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# Track uploaded files for cleanup and status
uploaded_files: dict[str, dict] = {}

# Directory for processed files
PROCESSED_DIR = Path(tempfile.gettempdir()) / "ifc_processed"
PROCESSED_DIR.mkdir(exist_ok=True)

# Initialize IFC processor
ifc_processor = IFCProcessor(output_dir=PROCESSED_DIR)

# Initialize job manager for async validation tasks
job_manager = JobManager()

# Initialize IDS validator for validation tasks
ids_validator = IDSValidator()

# Temp directory for validation job files
VALIDATION_DIR = Path(tempfile.gettempdir()) / "ids_validation_jobs"
VALIDATION_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "status": "healthy",
        "service": "IFC Validation API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "upload": "/api/upload",
            "status": "/api/status/{file_id}",
            "validate": "/api/v1/validate",
            "job_status": "/api/v1/jobs/{job_id}",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


@app.get("/api/health")
async def detailed_health_check():
    """Detailed API health check with system information."""
    return {
        "status": "ok",
        "upload_dir": str(UPLOAD_DIR),
        "upload_dir_exists": UPLOAD_DIR.exists(),
        "processed_dir": str(PROCESSED_DIR),
        "files_tracked": len(uploaded_files),
        "processor_capabilities": ifc_processor.get_capabilities(),
    }


@app.post("/api/upload")
async def upload_ifc(
    ifc_file: UploadFile = File(..., description="IFC file to process"),  # noqa: B008
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
        raise HTTPException(
            status_code=400, detail=f"Error reading file: {str(e)}"
        ) from None

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
        raise HTTPException(
            status_code=500, detail=f"Error saving file: {str(e)}"
        ) from None

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
            ) from None

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


@app.post("/api/process/{file_id}")
async def process_ifc(
    file_id: str,
    output_format: str = Query(
        "auto",
        description="Output format: 'auto', 'gltf', or 'json-mesh'",
        pattern="^(auto|gltf|json-mesh)$",
    ),
):
    """
    Process an uploaded IFC file to optimized geometry format.

    Converts IFC to browser-optimized format:
    - **gltf**: Binary glTF format (if available in ifcopenshell build)
    - **json-mesh**: JSON with triangulated geometry for Three.js
    - **auto**: Tries glTF first, falls back to JSON

    Returns:
        Processing result with geometry data or path to output file
    """
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    file_info = uploaded_files[file_id]
    ifc_path = file_info["file_path"]

    if not Path(ifc_path).exists():
        raise HTTPException(
            status_code=404, detail=f"IFC file no longer exists: {file_id}"
        )

    # Process the IFC file
    result = ifc_processor.process(
        ifc_path=ifc_path,
        output_name=file_id,
        preferred_format=output_format,
    )

    # Update file tracking with processing result
    file_info["processing_status"] = "completed" if result.success else "failed"
    file_info["processing_result"] = {
        "success": result.success,
        "format": result.output_format,
        "processing_time_ms": result.processing_time_ms,
        "element_count": result.element_count,
        "vertex_count": result.vertex_count,
        "face_count": result.face_count,
        "output_size_bytes": result.file_size_bytes,
        "error": result.error,
    }
    if result.output_path:
        file_info["processed_file_path"] = result.output_path

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {result.error}",
        )

    # Build response
    response = {
        "success": True,
        "file_id": file_id,
        "filename": file_info["original_filename"],
        "format": result.output_format,
        "processing_time_ms": result.processing_time_ms,
        "stats": {
            "elements": result.element_count,
            "vertices": result.vertex_count,
            "faces": result.face_count,
            "output_size_bytes": result.file_size_bytes,
            "output_size_mb": round(result.file_size_bytes / 1024 / 1024, 2),
        },
    }

    # Include geometry data or file path
    if result.output_format == "json-mesh" and result.output_data:
        response["geometry"] = result.output_data
    elif result.output_path:
        response["output_file"] = f"/api/download/{file_id}"
        response["output_path"] = result.output_path

    return JSONResponse(content=response)


@app.get("/api/download/{file_id}")
async def download_processed(file_id: str):
    """
    Download a processed geometry file (glTF/GLB).

    Args:
        file_id: UUID of the processed file
    """
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    file_info = uploaded_files[file_id]

    if "processed_file_path" not in file_info:
        raise HTTPException(
            status_code=404, detail=f"File not yet processed: {file_id}"
        )

    processed_path = Path(file_info["processed_file_path"])
    if not processed_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Processed file no longer exists: {file_id}"
        )

    # Determine media type
    media_type = "application/octet-stream"
    if processed_path.suffix.lower() == ".glb":
        media_type = "model/gltf-binary"
    elif processed_path.suffix.lower() == ".gltf":
        media_type = "model/gltf+json"

    return FileResponse(
        path=str(processed_path),
        media_type=media_type,
        filename=processed_path.name,
    )


@app.get("/api/capabilities")
async def get_capabilities():
    """
    Get server processing capabilities.

    Returns available output formats and processing options.
    """
    return {
        "formats": {
            "gltf": {
                "available": GLTF_AVAILABLE,
                "description": "Binary glTF format, optimal for large models",
                "file_extension": ".glb",
            },
            "json-mesh": {
                "available": True,
                "description": "JSON triangulated mesh for Three.js",
                "file_extension": None,  # Returned inline
            },
        },
        "recommended_format": "gltf" if GLTF_AVAILABLE else "json-mesh",
        "processor": ifc_processor.get_capabilities(),
    }


def run_validation_task(job_id: str, ifc_path: Path, ids_path: Path) -> None:
    """
    Background task to run IDS validation.

    This function is executed in a background task and handles:
    - Starting the job (marking as processing)
    - Running validation
    - Completing/failing the job with results
    - Cleaning up temp files

    Args:
        job_id: UUID of the job to process
        ifc_path: Path to the IFC file
        ids_path: Path to the IDS file
    """
    job_dir = ifc_path.parent

    try:
        # Mark job as processing
        job_manager.start_job(job_id)
        job_manager.update_progress(job_id, "Starting validation...")

        logger.info(f"Starting validation for job {job_id}")

        # Run validation
        job_manager.update_progress(job_id, "Validating IFC against IDS specification...")
        report = ids_validator.validate(ifc_path, ids_path)

        # Check if validation itself failed
        if not report.success:
            logger.warning(f"Validation failed for job {job_id}: {report.error}")
            job_manager.fail_job(job_id, report.error or "Unknown validation error")
            return

        # Validation completed successfully - convert to dict for storage
        result = report_to_dict(report)

        # Complete job with result
        job_manager.complete_job(job_id, result)
        logger.info(f"Validation completed for job {job_id}")

    except Exception as e:
        logger.error(f"Error during validation for job {job_id}: {str(e)}")
        job_manager.fail_job(job_id, f"Validation error: {str(e)}")

    finally:
        # Clean up temp files
        try:
            if job_dir.exists():
                shutil.rmtree(job_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {job_dir}: {str(e)}")


def convert_report_to_result(
    report: ValidationReport,
    ifc_filename: str,
    ids_filename: str,
) -> ValidationResult:
    """
    Convert a ValidationReport dataclass to a ValidationResult Pydantic model.

    This function maps the internal validation report structure (dataclass) to
    the API response model (Pydantic). Key mappings:
    - ValidationReport.success (ran) -> ValidationResult.success (all passed)
    - SpecificationResult dataclass -> SpecificationResult Pydantic (nested)
    - EntityFailure -> ElementResult for failed element details

    Args:
        report: The ValidationReport dataclass from IDSValidator
        ifc_filename: Original IFC filename for response
        ids_filename: Original IDS filename (or standard name) for response

    Returns:
        ValidationResult Pydantic model ready for JSON serialization
    """
    # Convert each specification from dataclass to Pydantic model
    spec_results: list[SpecificationResult] = []
    total_elements_validated = 0

    for spec in report.specifications:
        # Track total elements validated across all specifications
        total_elements_validated += spec.applicable_count

        # Convert EntityFailure dataclass items to ElementResult Pydantic models
        element_results: list[ElementResult] = []
        for failure in spec.failures:
            element_results.append(
                ElementResult(
                    entity_id=failure.entity_id,
                    entity_type=failure.entity_type,
                    failed_requirements=[
                        RequirementResult(
                            requirement_id=req.requirement_id,
                            requirement_description=req.description,
                            severity=SeverityLevel(req.severity.lower()) if hasattr(req.severity, 'lower') else SeverityLevel.ERROR,
                            failed=True,
                        )
                        for req in failure.requirements
                    ],
                )
            )

        # Determine specification status based on failures
        spec_status = ValidationStatus.PASSED if not element_results else ValidationStatus.FAILED

        spec_results.append(
            SpecificationResult(
                name=spec.name,
                description=spec.description or "",
                status=spec_status,
                applicable_count=spec.applicable_count,
                failed_count=len(element_results),
                passed_count=spec.applicable_count - len(element_results),
                elements=element_results,
            )
        )

    # Overall validation status
    all_passed = all(spec.status == ValidationStatus.PASSED for spec in spec_results)
    overall_status = ValidationStatus.PASSED if all_passed else ValidationStatus.FAILED

    return ValidationResult(
        status=overall_status,
        ifc_filename=ifc_filename,
        ids_filename=ids_filename,
        total_elements_validated=total_elements_validated,
        specifications=spec_results,
        validation_time_ms=report.validation_time_ms,
        validator_version=getattr(report, 'validator_version', '1.0.0'),
    )


@app.post("/api/v1/validate")
async def validate_ifc_ids(
    ifc_file: UploadFile = File(..., description="IFC file to validate"),  # noqa: B008
    ids_file: Optional[UploadFile] = File(None, description="IDS file for validation"),  # noqa: B008
    standard: Optional[str] = Query(None, description="IDS standard name (e.g., 'IFC4.3', 'common')"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Validate an IFC file against IDS specifications (asynchronously).

    Either provide an IDS file or specify a standard to use.

    Returns:
        Job ID for checking validation status via /api/v1/jobs/{job_id}
    """
    # Validate IFC file
    if not ifc_file.filename or not ifc_file.filename.lower().endswith('.ifc'):
        raise HTTPException(status_code=400, detail="Valid IFC file required")

    # Create job directory
    job_id = str(uuid.uuid4())
    job_dir = VALIDATION_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    try:
        # Save IFC file
        ifc_content = await ifc_file.read()
        if not ifc_content:
            raise HTTPException(status_code=400, detail="IFC file is empty")
        if len(ifc_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="IFC file too large")

        ifc_path = job_dir / ifc_file.filename
        with open(ifc_path, "wb") as f:
            f.write(ifc_content)

        # Determine IDS file path
        ids_path: Optional[Path] = None
        ids_filename = "specification.ids"

        if ids_file:
            # Use uploaded IDS file
            if not ids_file.filename or not ids_file.filename.lower().endswith('.ids'):
                raise HTTPException(status_code=400, detail="Valid IDS file required")

            ids_content = await ids_file.read()
            if not ids_content:
                raise HTTPException(status_code=400, detail="IDS file is empty")
            if len(ids_content) > MAX_IDS_FILE_SIZE:
                raise HTTPException(status_code=413, detail="IDS file too large")

            ids_filename = ids_file.filename
            ids_path = job_dir / ids_filename
            with open(ids_path, "wb") as f:
                f.write(ids_content)

        elif standard:
            # Use bundled standard IDS
            ids_path = get_bundled_ids(standard)
            if not ids_path:
                raise HTTPException(status_code=400, detail=f"Unknown standard: {standard}")
            ids_filename = f"{standard}.ids"

        else:
            raise HTTPException(
                status_code=400,
                detail="Either provide IDS file or specify a standard"
            )

        # Create job and schedule background task
        job_manager.create_job(
            job_id=job_id,
            ifc_filename=ifc_file.filename,
            ids_filename=ids_filename,
        )

        background_tasks.add_task(
            run_validation_task,
            job_id=job_id,
            ifc_path=ifc_path,
            ids_path=ids_path,
        )

        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "status": "queued",
                "status_url": f"/api/v1/jobs/{job_id}",
            }
        )

    except HTTPException:
        # Clean up on validation errors
        if job_dir.exists():
            shutil.rmtree(job_dir)
        raise
    except Exception as e:
        # Clean up on unexpected errors
        if job_dir.exists():
            shutil.rmtree(job_dir)
        logger.error(f"Error in validation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the status of a validation job.

    Args:
        job_id: UUID of the validation job

    Returns:
        Job status with results if completed
    """
    job_status = job_manager.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return job_status