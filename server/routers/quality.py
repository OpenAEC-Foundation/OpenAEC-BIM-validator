"""Data quality check API router.

Exposes a synchronous endpoint that runs the
:mod:`ifc_validator.quality` checks against an uploaded IFC model and
returns the resulting :class:`~ifc_validator.quality.models.QualityReport`
as JSON.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from ifc_validator.quality import run_quality_checks
from ifc_validator.quality.models import QualityReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["quality"])

ALLOWED_EXTENSIONS = {".ifc", ".ifcx"}


@router.post("/quality", response_model=QualityReport)
async def run_quality(
    ifc_file: UploadFile = File(..., description="IFC model to analyse"),
    checks: str | None = Form(
        None,
        description="Comma-separated check ids to run (default: all checks)",
    ),
) -> QualityReport:
    """Run data quality checks on an uploaded IFC file.

    The upload is spooled to a temporary file, analysed synchronously in
    a worker thread, and the temporary file is removed afterwards.

    Args:
        ifc_file: Multipart IFC file upload.
        checks: Optional comma-separated list of check ids (e.g.
            ``duplicate_globalids,no_material``). Unknown ids yield 400.

    Returns:
        The quality report for the uploaded model.
    """
    if not ifc_file.filename:
        raise HTTPException(400, "Filename is required")

    ext = Path(ifc_file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Invalid extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    selected: list[str] | None = None
    if checks:
        selected = [c.strip() for c in checks.split(",") if c.strip()] or None

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            tmp_path = tmp.name
            await run_in_threadpool(shutil.copyfileobj, ifc_file.file, tmp)

        if os.path.getsize(tmp_path) == 0:
            raise HTTPException(400, "File is empty")

        try:
            report = await run_in_threadpool(
                run_quality_checks, tmp_path, selected
            )
        except ValueError as exc:
            # Unknown check id(s) in the checks filter.
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            logger.exception(
                "Quality check failed for upload %s", ifc_file.filename
            )
            raise HTTPException(
                422, f"Could not process IFC file: {exc}"
            ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    logger.info(
        "Quality checks for %s: %d errors, %d warnings",
        ifc_file.filename,
        report.error_count,
        report.warning_count,
    )

    # Report the original upload name instead of the temp path.
    return report.model_copy(update={"ifc_file": ifc_file.filename})
