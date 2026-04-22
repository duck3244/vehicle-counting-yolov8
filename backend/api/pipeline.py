"""VehicleCountingSystem 어댑터 — 잡 실행기에서 사용한다.

주요 책임:
- 옵션을 VehicleCountingSystem config override 로 변환.
- 진행률 콜백 주입.
- 결과 파일 경로 규약:
    outputs/{job_id}/result.mp4           (브라우저 호환 H.264, 가능한 경우)
    outputs/{job_id}/results.json          (카운팅 통계)
    outputs/{job_id}/results_chart.png     (파이/막대 차트)
    outputs/{job_id}/results_hourly.png    (시간별 차트)
- 결과 영상은 OpenCV 로 저장 후 ffmpeg 가 있으면 H.264 재인코딩을 시도한다.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# backend/ 를 import path 에 올려 main_system 을 모듈로 가져온다.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main_system import VehicleCountingSystem  # noqa: E402  (path 조작 이후)

from .schemas import JobOptions

CONFIG_PATH = BACKEND_DIR / "config.yaml"

ProgressCb = Callable[[float, int, int], None]


def _build_override(output_dir: Path, options: JobOptions) -> Dict[str, Any]:
    """API 옵션을 VehicleCountingSystem.update_config 용 dict 로 변환."""
    results_prefix = str(output_dir / "results")
    override: Dict[str, Any] = {
        "video": {"display_realtime": False, "save_output": True},
        "output": {"save_results": True, "results_file": results_prefix},
        "debug": {"skip_logging_setup": True},  # uvicorn 쪽 로깅 존중
    }
    if options.lanes is not None:
        override["lanes"] = {"mode": "auto", "count": options.lanes}
    if options.confidence_threshold is not None:
        override.setdefault("model", {})[
            "confidence_threshold"
        ] = options.confidence_threshold
    if options.model_path:
        override.setdefault("model", {})["path"] = options.model_path
    return override


def _transcode_h264(src: Path, dst: Path) -> bool:
    """ffmpeg 로 H.264(faststart) 재인코딩. 실패 시 False 반환."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return False
    try:
        subprocess.run(
            [
                ffmpeg, "-y", "-i", str(src),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-movflags", "+faststart",
                "-c:a", "copy",  # 오디오 없으면 무시됨
                str(dst),
            ],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode(errors="ignore")[:500]
        logging.warning("ffmpeg 재인코딩 실패: %s", stderr)
        return False


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    options: JobOptions,
    progress_cb: Optional[ProgressCb] = None,
) -> Dict[str, Any]:
    """잡 1건을 실행. 블로킹 함수 — 호출자 쪽에서 별도 스레드로 돌려야 한다."""
    system = VehicleCountingSystem(str(CONFIG_PATH))
    system.update_config(_build_override(output_dir, options))
    if progress_cb is not None:
        system.progress_callback = progress_cb

    raw_output = output_dir / "result_raw.mp4"
    web_output = output_dir / "result.mp4"

    ok = system.process_video(str(input_path), str(raw_output))
    if not ok:
        raise RuntimeError("비디오 처리 실패")

    # 브라우저 호환 재인코딩 시도
    if _transcode_h264(raw_output, web_output):
        raw_output.unlink(missing_ok=True)
    else:
        # ffmpeg 가 없거나 실패 → 원본을 그대로 노출
        raw_output.replace(web_output)

    # 통계 JSON 읽어 일부 필드만 응답에 포함
    stats_path = output_dir / "results.json"
    stats: Optional[Dict[str, Any]] = None
    if stats_path.is_file():
        try:
            with stats_path.open("r", encoding="utf-8") as f:
                stats = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("결과 JSON 로드 실패: %s", exc)

    job_id = output_dir.name
    artifacts = {
        "video": f"/static/{job_id}/result.mp4",
        "results_json": f"/static/{job_id}/results.json",
    }
    for extra in ("results_chart.png", "results_hourly.png"):
        if (output_dir / extra).is_file():
            artifacts[extra.replace(".png", "")] = f"/static/{job_id}/{extra}"

    return {
        "artifacts": artifacts,
        "summary": stats.get("statistics") if stats else None,
        "total_counts": stats.get("total_counts") if stats else None,
        "session": stats.get("session_info") if stats else None,
    }
