"""Async clash-detection endpoints (ifcclash).

Upload one IFC (clashes within the model, e.g. between disciplines) or
two IFCs (model A against model B). Same job pattern as the optimizer:
202 with job id → poll → results in the job body. Geometry processing
runs locally via IfcOpenShell; typical runtime is seconds to minutes
depending on model size.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from server.routers.jobstore import Job, JobStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clash", tags=["clash"])

CLASH_DIR = Path(tempfile.gettempdir()) / "ids_clash_jobs"
MAX_FILE_SIZE = 500 * 1024 * 1024
MAX_RESULTS = 2000

CLASH_MODES = ("intersection", "collision", "clearance")


def _cleanup_job_files(job: Job) -> None:
    job_dir = job.artifacts.get("job_dir")
    if job_dir:
        shutil.rmtree(job_dir, ignore_errors=True)


jobs = JobStore(on_expire=_cleanup_job_files)


def _run_clash_task(
    job_id: str,
    path_a: Path,
    path_b: Optional[Path],
    mode: str,
    tolerance: float,
    clearance: float,
) -> None:
    """Background task: run ifcclash and store a JSON-friendly result."""
    try:
        jobs.start(job_id)

        from ifcclash.ifcclash import Clasher, ClashSettings

        settings = ClashSettings()
        settings.logger = logger
        clasher = Clasher(settings)

        clash_set: dict = {
            "name": "A vs B" if path_b else "Binnen model",
            "a": [{"file": str(path_a)}],
            "mode": mode,
            "check_all": False,
        }
        if path_b:
            clash_set["b"] = [{"file": str(path_b)}]
        if mode == "intersection":
            clash_set["tolerance"] = tolerance
        elif mode == "clearance":
            clash_set["clearance"] = clearance

        clasher.clash_sets = [clash_set]
        clasher.clash()

        raw = clash_set.get("clashes", {}) or {}
        clashes = []
        for clash in raw.values():
            clashes.append(
                {
                    "a_global_id": clash["a_global_id"],
                    "b_global_id": clash["b_global_id"],
                    "a_ifc_class": clash["a_ifc_class"],
                    "b_ifc_class": clash["b_ifc_class"],
                    "a_name": clash["a_name"],
                    "b_name": clash["b_name"],
                    "type": str(clash["type"]),
                    "position": list(clash.get("p1") or []),
                    "distance": clash.get("distance"),
                }
            )
            if len(clashes) >= MAX_RESULTS:
                break

        result = {
            "mode": mode,
            "clash_count": len(raw),
            "clashes": clashes,
            "results_omitted": max(len(raw) - len(clashes), 0),
        }
        jobs.complete(job_id, result)
        logger.info("Clash job %s completed: %d clashes", job_id, len(raw))
    except Exception as exc:
        logger.error("Clash job %s failed: %s", job_id, exc)
        jobs.fail(job_id, str(exc))
    finally:
        # Model files are no longer needed once results are in memory
        job = jobs.get(job_id)
        if job:
            _cleanup_job_files(job)


async def _save_upload(upload: UploadFile, job_dir: Path) -> Path:
    if not upload.filename or not upload.filename.lower().endswith(".ifc"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {upload.filename or 'unknown'}."
            " Expected .ifc file",
        )
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="IFC file is empty")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="IFC file too large")
    path = job_dir / Path(upload.filename).name
    path.write_bytes(content)
    return path


@router.post("")
async def start_clash(
    ifc_a: UploadFile = File(..., description="First IFC model"),  # noqa: B008
    ifc_b: Optional[UploadFile] = File(  # noqa: B008
        None, description="Second IFC model (omit to clash within the first)"
    ),
    mode: str = Form("intersection"),
    tolerance: float = Form(0.002),
    clearance: float = Form(0.05),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> JSONResponse:
    """Queue a clash-detection job."""
    if mode not in CLASH_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown mode: {mode!r}. Valid: {', '.join(CLASH_MODES)}",
        )

    job = jobs.create()
    job_dir = CLASH_DIR / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    job.artifacts["job_dir"] = str(job_dir)

    try:
        path_a = await _save_upload(ifc_a, job_dir)
        path_b = await _save_upload(ifc_b, job_dir) if ifc_b else None
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    background_tasks.add_task(
        _run_clash_task,
        job_id=job.job_id,
        path_a=path_a,
        path_b=path_b,
        mode=mode,
        tolerance=tolerance,
        clearance=clearance,
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job.job_id,
            "status": "pending",
            "status_url": f"/api/v1/clash/jobs/{job.job_id}",
        },
    )


@router.get("/jobs/{job_id}")
async def get_clash_job(job_id: str) -> JSONResponse:
    """Poll a clash job; completed jobs include the clash list."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    body: dict = {"job_id": job.job_id, "status": job.status}
    if job.status == "completed":
        body["result"] = job.result
    elif job.status == "failed":
        body["error"] = job.error
    return JSONResponse(content=body)
