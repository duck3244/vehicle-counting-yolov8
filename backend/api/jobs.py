"""In-memory 잡 레지스트리와 단일 워커 실행기.

MVP 범위:
- 단일 GPU 가정 → ThreadPoolExecutor(max_workers=1) 로 순차 실행.
- 영속화 없음(프로세스 재시작 시 잡 이력 소실).
- 진행률은 파이프라인의 progress_callback 을 통해 Job 필드로 반영되며,
  클라이언트는 GET /api/jobs/{id} 폴링으로 확인한다.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import Job, JobOptions, JobStatus

BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
OUTPUT_DIR = BACKEND_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job-")

    def create(self, filename: str, options: JobOptions) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            status=JobStatus.queued,
            filename=filename,
            created_at=datetime.now(timezone.utc),
            options=options,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> List[Job]:
        with self._lock:
            return sorted(
                self._jobs.values(), key=lambda j: j.created_at, reverse=True
            )

    def _update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            self._jobs[job_id] = job.model_copy(update=kwargs)

    def submit(self, job_id: str, input_path: Path) -> None:
        self._executor.submit(self._run, job_id, input_path)

    def _run(self, job_id: str, input_path: Path) -> None:
        # 순환 의존을 피하기 위해 런타임 임포트
        from .pipeline import run_pipeline

        self._update(
            job_id,
            status=JobStatus.running,
            started_at=datetime.now(timezone.utc),
        )

        def progress_cb(ratio: float, current: int, total: int) -> None:
            self._update(
                job_id, progress=ratio, current_frame=current, total_frames=total
            )

        job = self.get(job_id)
        if job is None:  # 방어적
            return

        output_dir = OUTPUT_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = run_pipeline(
                input_path=input_path,
                output_dir=output_dir,
                options=job.options,
                progress_cb=progress_cb,
            )
            self._update(
                job_id,
                status=JobStatus.done,
                finished_at=datetime.now(timezone.utc),
                progress=1.0,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001 - job 실패는 여기서 포착해 저장
            logging.exception("잡 실행 실패 (%s): %s", job_id, exc)
            self._update(
                job_id,
                status=JobStatus.error,
                finished_at=datetime.now(timezone.utc),
                error=str(exc),
            )


registry = JobRegistry()
