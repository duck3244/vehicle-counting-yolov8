"""잡 관련 라우트 — 업로드/목록/상세."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..jobs import UPLOAD_DIR, registry
from ..schemas import Job, JobOptions

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_CHUNK = 1024 * 1024  # 1 MiB


@router.post("", response_model=Job, status_code=201)
async def create_job(
    file: UploadFile = File(...),
    lanes: Optional[int] = Form(default=None),
    confidence_threshold: Optional[float] = Form(default=None),
    model_path: Optional[str] = Form(default=None),
) -> Job:
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 형식입니다: {ext or '(없음)'}",
        )

    # Form 파라미터는 Pydantic Field 제약을 자동 적용하지 않으므로 수동 검증.
    if lanes is not None and not (1 <= lanes <= 20):
        raise HTTPException(
            status_code=422, detail="lanes 는 1 ~ 20 범위여야 합니다."
        )
    if confidence_threshold is not None and not (
        0.0 <= confidence_threshold <= 1.0
    ):
        raise HTTPException(
            status_code=422,
            detail="confidence_threshold 는 0.0 ~ 1.0 범위여야 합니다.",
        )

    options = JobOptions(
        lanes=lanes,
        confidence_threshold=confidence_threshold,
        model_path=model_path,
    )
    job = registry.create(filename=file.filename, options=options)

    saved_path = UPLOAD_DIR / f"{job.id}{ext}"
    async with aiofiles.open(saved_path, "wb") as f:
        while chunk := await file.read(MAX_CHUNK):
            await f.write(chunk)

    registry.submit(job.id, saved_path)
    return job


@router.get("", response_model=List[Job])
def list_jobs() -> List[Job]:
    return registry.list()


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="잡을 찾을 수 없습니다.")
    return job
