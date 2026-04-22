"""설정 파일 조회 라우트 (MVP: 읽기 전용)."""

from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException

from ..pipeline import CONFIG_PATH

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise HTTPException(status_code=404, detail="config.yaml 이 없습니다.")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
