"""Pydantic 스키마 — API 경계에서의 데이터 모델."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"


class JobOptions(BaseModel):
    lanes: Optional[int] = Field(default=None, ge=1, le=20)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    model_path: Optional[str] = None


class Job(BaseModel):
    id: str
    status: JobStatus
    filename: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 ~ 1.0
    current_frame: int = 0
    total_frames: int = 0
    message: Optional[str] = None
    options: JobOptions = Field(default_factory=JobOptions)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    gpu: Optional[str] = None
    version: str = "0.1.0"
