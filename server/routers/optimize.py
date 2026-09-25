"""Async IFC-optimizer endpoints.

Same job pattern as /api/v1/validate: upload → 202 with job id → poll →
download the optimized file. The original upload and the optimized
result live in a per-job temp directory that is removed on job expiry.
"""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ifc_validator.optimizer import PASS_ORDER, list_passes, optimize
from server.routers.jobstore import Job, JobStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/optimize", tags=["optimize"])

OPTIMIZE_DIR = Path(tempfile.gettempdir()) / "ids_optimize_jobs"
MAX_FILE_SIZE = 500 * 1024 * 1024  # matches the validation upload cap


def _cleanup_job_files(job: Job) -> None:
    job_dir = job.artifacts.get("job_dir")
    if job_dir:
        shutil.rmtree(job_dir, ignore_errors=True)


jobs = JobStore(on_expire=_cleanup_job_files)


def _run_optimize_task(
    job_id: str, input_path: Path, output_path: Path, passes: list[str]
) -> None:
    """Background task: run the optimizer and store the report."""
    try:
        jobs.start(job_id)
        report = optimize(input_path, output_path, passes=passes)
        jobs.complete(job_id, report.model_dump())
        logger.info("Optimize job %s completed", job_id)
    except Exception as exc:
        logger.error("Optimize job %s failed: %s", job_id, exc)
        jobs.fail(job_id, str(exc))


@router.get("/passes")
async def get_passes() -> JSONResponse:
    """List the available optimizer passes for UI selection."""
    return JSONResponse(content={"passes": list_passes()})


@router.post("")
async def start_optimize(
    ifc_file: UploadFile = File(..., description="IFC file to optimize"),  # noqa: B008
    passes: str = Form("", description="Comma-separated pass names; empty = all"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> JSONResponse:
    """Queue an optimize job for the uploaded IFC file."""
    if not ifc_file.filename or not ifc_file.filename.lower().endswith(".ifc"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {ifc_file.filename or 'unknown'}."
            " Expected .ifc file",
        )

    selected = [p.strip() for p in passes.split(",") if p.strip()] or None
    if selected:
        unknown = [p for p in selected if p not in PASS_ORDER]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown pass(es): {', '.join(unknown)}."
                f" Valid: {', '.join(PASS_ORDER)}",
            )

    content = await ifc_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="IFC file is empty")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="IFC file too large")

    job = jobs.create()
    job_dir = OPTIMIZE_DIR / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    job.artifacts["job_dir"] = str(job_dir)

    input_path = job_dir / Path(ifc_file.filename).name
    stem = input_path.stem
    output_path = job_dir / f"{stem}.optimized.ifc"
    job.artifacts["output_path"] = str(output_path)
    job.artifacts["output_name"] = output_path.name

    try:
        input_path.write_bytes(content)
    except OSError as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Could not store upload: {exc}")

    background_tasks.add_task(
        _run_optimize_task,
        job_id=job.job_id,
        input_path=input_path,
        output_path=output_path,
        passes=selected or list(PASS_ORDER),
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job.job_id,
            "status": "pending",
            "status_url": f"/api/v1/optimize/jobs/{job.job_id}",
        },
    )


@router.get("/jobs/{job_id}")
async def get_optimize_job(job_id: str) -> JSONResponse:
    """Poll an optimize job; completed jobs include the full report."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    body: dict = {"job_id": job.job_id, "status": job.status}
    if job.status == "completed":
        body["report"] = job.result
        body["download_url"] = f"/api/v1/optimize/jobs/{job.job_id}/download"
    elif job.status == "failed":
        body["error"] = job.error
    return JSONResponse(content=body)


@router.get("/jobs/{job_id}/download")
async def download_optimized(job_id: str) -> FileResponse:
    """Download the optimized IFC file of a completed job."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    if job.status != "completed":
        raise HTTPException(
            status_code=409, detail=f"Job is {job.status}, not completed"
        )

    output_path = Path(job.artifacts["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=410, detail="Result file no longer exists")

    return FileResponse(
        path=output_path,
        filename=job.artifacts["output_name"],
        media_type="application/octet-stream",
    )
