"""FastAPI 진입점. ``uvicorn api.main:app`` 로 실행한다."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from .jobs import OUTPUT_DIR  # noqa: E402  (sys.path 조작 이후)
from .routes.config import router as config_router  # noqa: E402
from .routes.jobs import router as jobs_router  # noqa: E402
from .schemas import HealthResponse  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Vehicle Counting API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(config_router)

# 잡별 산출물을 그대로 서빙 (MVP)
app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    gpu: str | None = None
    try:
        import torch  # 지연 임포트

        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
    except Exception:  # noqa: BLE001
        gpu = None
    return HealthResponse(status="ok", gpu=gpu)
