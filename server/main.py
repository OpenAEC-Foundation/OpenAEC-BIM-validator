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
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from server.ifc_processor import GLTF_AVAILABLE, IFCProcessor
from server.ids_validator import IDSValidator, ValidationReport
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
                    global_id=failure.global_id,
                    element_type=failure.entity_type,
                    element_name=failure.entity_name,
                    status=ValidationStatus.FAIL,
                    messages=[],  # No specific messages available from ifctester
                )
            )

        # Create a single requirement result that contains all element results
        # Note: ifctester doesn't expose requirement-level granularity,
        # so we wrap all elements in a single "requirement" per specification
        requirement_result = RequirementResult(
            requirement_description=spec.description or spec.name,
            status=ValidationStatus.PASS if spec.passed else ValidationStatus.FAIL,
            total_elements=spec.applicable_count,
            failed_elements=spec.failed_count,
            elements=element_results,
        )

        # Map specification status to ValidationStatus enum
        spec_status = ValidationStatus.PASS if spec.passed else ValidationStatus.FAIL

        # Create Pydantic SpecificationResult
        # Note: severity defaults to ERROR as ifctester doesn't expose this
        spec_result = SpecificationResult(
            specification_name=spec.name,
            severity=SeverityLevel.ERROR,
            status=spec_status,
            total_requirements=1,  # Each spec treated as one requirement
            failed_requirements=0 if spec.passed else 1,
            requirements=[requirement_result],
        )
        spec_results.append(spec_result)

    # Calculate success: all specifications must have passed
    all_passed = report.failed_specifications == 0

    return ValidationResult(
        success=all_passed,
        total_specifications=report.total_specifications,
        failed_specifications=report.failed_specifications,
        total_elements_validated=total_elements_validated,
        validation_timestamp=report.timestamp,
        specifications=spec_results,
        ifc_file_name=ifc_filename,
        ids_file_name=ids_filename,
    )


@app.post("/api/v1/validate")
async def validate_ifc(
    ifc_file: UploadFile = File(..., description="IFC file to validate"),  # noqa: B008
    ids_file: Optional[UploadFile] = File(  # noqa: B008
        None, description="IDS file with validation rules (optional if ids_standard provided)"
    ),
    ids_standard: Optional[str] = Query(  # noqa: B008
        None,
        description="Built-in IDS standard to use: 'nl-bim' or 'rvb' (optional if ids_file provided)",
    ),
):
    """
    Validate an IFC file against IDS specifications.

    Accepts an IFC file and validates it against either:
    - A custom IDS file uploaded via `ids_file`, OR
    - A built-in Dutch BIM standard specified via `ids_standard`

    At least one of `ids_file` or `ids_standard` must be provided.

    Args:
        ifc_file: The IFC file to validate (required, max 500MB)
        ids_file: Custom IDS file with validation rules (optional, max 5MB)
        ids_standard: Built-in standard - "nl-bim" or "rvb" (optional)

    Returns:
        ValidationResult with pass/fail counts and detailed specification results

    Raises:
        400: Missing required files or invalid parameters
        413: File too large
        422: Corrupt or invalid file content
    """
    # === IFC FILE VALIDATION (Subtask 2.1) ===

    # Check filename exists
    if not ifc_file.filename:
        raise HTTPException(
            status_code=400,
            detail="IFC filename is required",
        )

    # Validate file extension (.ifc, .ifcxml, or .ifczip)
    ifc_filename_lower = ifc_file.filename.lower()
    valid_ifc_extensions = (".ifc", ".ifcxml", ".ifczip")
    if not ifc_filename_lower.endswith(valid_ifc_extensions):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid IFC file type. Expected .ifc, .ifcxml, or .ifczip file, "
                f"got: {ifc_file.filename}"
            ),
        )

    # Read file content
    try:
        ifc_content = await ifc_file.read()
        ifc_file_size = len(ifc_content)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error reading IFC file: {str(e)}",
        ) from None

    # Check file size against MAX_FILE_SIZE (500MB)
    if ifc_file_size > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE / 1024 / 1024
        actual_size_mb = ifc_file_size / 1024 / 1024
        raise HTTPException(
            status_code=413,
            detail=(
                f"IFC file too large. Maximum size is {max_size_mb:.0f}MB, "
                f"got {actual_size_mb:.1f}MB"
            ),
        )

    # Check file is not empty
    if ifc_file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="IFC file is empty",
        )

    # === IDS FILE/STANDARD VALIDATION (Subtask 2.2) ===

    # Either ids_file OR ids_standard must be provided
    if ids_file is None and ids_standard is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Either ids_file or ids_standard must be provided. "
                "Upload an IDS file or specify a standard: 'nl-bim' or 'rvb'"
            ),
        )

    # If ids_file provided, validate extension and size
    if ids_file is not None:
        # Check filename exists
        if not ids_file.filename:
            raise HTTPException(
                status_code=400,
                detail="IDS filename is required",
            )

        # Validate file extension (.ids or .xml)
        ids_filename_lower = ids_file.filename.lower()
        valid_ids_extensions = (".ids", ".xml")
        if not ids_filename_lower.endswith(valid_ids_extensions):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid IDS file type. Expected .ids or .xml file, "
                    f"got: {ids_file.filename}"
                ),
            )

        # Read file content to check size
        try:
            ids_content = await ids_file.read()
            ids_file_size = len(ids_content)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error reading IDS file: {str(e)}",
            ) from None

        # Check file size against MAX_IDS_FILE_SIZE (5MB)
        if ids_file_size > MAX_IDS_FILE_SIZE:
            max_size_mb = MAX_IDS_FILE_SIZE / 1024 / 1024
            actual_size_mb = ids_file_size / 1024 / 1024
            raise HTTPException(
                status_code=413,
                detail=(
                    f"IDS file too large. Maximum size is {max_size_mb:.0f}MB, "
                    f"got {actual_size_mb:.1f}MB"
                ),
            )

        # Check file is not empty
        if ids_file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="IDS file is empty",
            )

    # If ids_standard provided, validate it's a known standard
    if ids_standard is not None:
        valid_standards = ("nl-bim", "rvb")
        if ids_standard.lower() not in valid_standards:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid IDS standard: '{ids_standard}'. "
                    f"Valid options are: {', '.join(valid_standards)}"
                ),
            )

    # === SAVE UPLOADED FILES TO TEMP DIRECTORY (Subtask 3.1) ===

    # Track temp file paths for cleanup
    temp_files: list[Path] = []

    # Generate unique ID for this validation request
    validation_id = str(uuid.uuid4())

    # Save IFC file to temp directory
    safe_ifc_filename = f"{validation_id}_{ifc_file.filename.replace(' ', '_')}"
    ifc_temp_path = UPLOAD_DIR / safe_ifc_filename
    try:
        with open(ifc_temp_path, "wb") as f:
            f.write(ifc_content)
        temp_files.append(ifc_temp_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving IFC file to temp directory: {str(e)}",
        ) from None

    # Save IDS file to temp directory (if provided)
    ids_temp_path: Optional[Path] = None
    if ids_file is not None:
        safe_ids_filename = f"{validation_id}_{ids_file.filename.replace(' ', '_')}"
        ids_temp_path = UPLOAD_DIR / safe_ids_filename
        try:
            with open(ids_temp_path, "wb") as f:
                f.write(ids_content)
            temp_files.append(ids_temp_path)
        except Exception as e:
            # Clean up IFC file if IDS save fails
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=500,
                detail=f"Error saving IDS file to temp directory: {str(e)}",
            ) from None

    # === RESOLVE IDS PATH (Subtask 3.2) ===
    # Determine the IDS file path to use for validation
    # Priority: ids_file (uploaded custom) > ids_standard (bundled)
    if ids_temp_path is not None:
        # Use the uploaded custom IDS file
        ids_path_for_validation = ids_temp_path
    else:
        # Use bundled IDS based on ids_standard
        # ids_standard is guaranteed to be valid at this point (validated in 2.2)
        try:
            ids_path_for_validation = get_bundled_ids(ids_standard.lower())
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e),
            ) from None
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load bundled IDS standard: {str(e)}",
            ) from None

    # === RUN VALIDATION (Subtask 3.3) ===
    # Use IDSValidator to validate the IFC file against the IDS specification
    # Handle exceptions for corrupt/invalid files

    validator = IDSValidator()
    try:
        validation_report = validator.validate(ifc_temp_path, ids_path_for_validation)
    except FileNotFoundError as e:
        # This should not happen since we just saved the files, but handle defensively
        raise HTTPException(
            status_code=422,
            detail=f"File not found during validation: {str(e)}",
        ) from None
    except Exception as e:
        # Catch any unexpected exceptions during validation setup
        raise HTTPException(
            status_code=422,
            detail=f"Unexpected error during validation: {str(e)}",
        ) from None

    # Check if validation completed successfully
    # Note: report.success means validation RAN without errors, not pass/fail
    # Corrupt IFC or invalid IDS file results in success=False with error
    if not validation_report.success:
        raise HTTPException(
            status_code=422,
            detail=f"Validation failed: {validation_report.error}",
        )

    # === CONVERT VALIDATION REPORT TO RESPONSE (Subtask 3.4) ===
    # Determine the IDS filename for the response
    # Use original filename if uploaded, otherwise use standard name
    ids_response_filename = (
        ids_file.filename if ids_file is not None else f"{ids_standard}-standard.ids"
    )

    # Convert dataclass ValidationReport to Pydantic ValidationResult
    validation_result = convert_report_to_result(
        report=validation_report,
        ifc_filename=ifc_file.filename,
        ids_filename=ids_response_filename,
    )

    # TODO: Cleanup temp files (Subtask 4.1)

    # Return the ValidationResult as JSON response
    return validation_result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
