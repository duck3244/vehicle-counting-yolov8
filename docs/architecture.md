# 아키텍처 문서 — Vehicle Counting YOLOv8

본 문서는 `vehicle-counting-yolov8` 프로젝트의 전반적인 아키텍처, 모듈 구성, 데이터 흐름, 배포 토폴로지를 정리한 것이다. 파일/클래스 레벨 관계도는 [`uml.md`](./uml.md) 를 참고한다.

---

## 1. 개요

YOLOv8 기반의 **차선별 차량 감지·추적·카운팅 시스템**을 코어로 두고, 그 위에 다음 두 진입점을 제공한다.

| 진입점 | 설명 | 주 사용처 |
|---|---|---|
| CLI (`main_system.py`) | 비디오 파일/웹캠을 직접 처리하고 결과물을 로컬에 저장 | 오프라인 배치, 연구/실험 |
| REST API + SPA (`backend/api` + `frontend/`) | 비디오 업로드 → 잡 큐잉 → 폴링 기반 진행률 조회 → 결과물 시청 | 웹 MVP, 데모 |

두 진입점 모두 **동일한 코어 모듈**(`VehicleCountingSystem`)을 호출하여 결과의 일관성을 유지한다.

---

## 2. 디렉터리 구조

```
vehicle-counting-yolov8/
├── backend/
│   ├── detector.py          # YOLOv8 차량 감지
│   ├── tracker.py           # ID 기반 트래킹/경로/속도
│   ├── lane_manager.py      # 차선 설정·검증·라인 크로싱 판정
│   ├── counter.py           # 중복 방지 카운팅, 통계 집계
│   ├── visualizer.py        # OpenCV 오버레이 + matplotlib 차트
│   ├── main_system.py       # VehicleCountingSystem — 오케스트레이터 + CLI
│   ├── run_examples.py      # 대화형 예제 스크립트
│   ├── config.yaml          # 파이프라인 기본 설정
│   ├── requirements.txt
│   ├── uploads/             # (런타임) 업로드된 원본 비디오
│   ├── outputs/             # (런타임) 잡별 산출물 (outputs/{job_id}/...)
│   └── api/
│       ├── main.py          # FastAPI 진입점, CORS, static mount
│       ├── jobs.py          # In-memory JobRegistry + ThreadPoolExecutor
│       ├── pipeline.py      # VehicleCountingSystem 어댑터 + ffmpeg 재인코딩
│       ├── schemas.py       # Pydantic 모델 (Job / JobOptions / Health)
│       └── routes/
│           ├── jobs.py      # POST/GET /api/jobs, GET /api/jobs/{id}
│           └── config.py    # GET /api/config (read-only)
├── frontend/
│   ├── vite.config.ts       # /api, /static 프록시 → 127.0.0.1:8000
│   ├── package.json         # Vue 3 + Pinia + Vue Router + axios
│   └── src/
│       ├── main.ts          # createApp + Pinia + Router
│       ├── App.vue          # 상단 네비 + RouterView
│       ├── router/index.ts  # / , /jobs/:id
│       ├── api/client.ts    # axios 래퍼 (fetchHealth/listJobs/createJob/getJob)
│       ├── stores/jobs.ts   # Pinia jobs store
│       ├── types/index.ts   # 백엔드 Pydantic 미러 타입
│       └── views/
│           ├── HomeView.vue # 헬스체크 + 업로드 폼 + 잡 목록 폴링
│           └── JobView.vue  # 잡 상세 + 결과 영상/차트/카운트 표
└── docs/
    ├── architecture.md      # (이 문서)
    └── uml.md
```

---

## 3. 코어 파이프라인 (backend core)

`VehicleCountingSystem`(`backend/main_system.py`) 은 **5 개의 독립 모듈**을 조합해 비디오 한 프레임을 다음 순서로 처리한다.

```
프레임 입력
   │
   ▼
[1] VehicleDetector.detect_vehicles(frame, track=True)
       - YOLOv8.track() 호출 → 차량 클래스(car/truck/bus/motorcycle)만 필터
       - bbox, confidence, track_id, center, area 를 담은 dict 리스트 반환
   │
   ▼
[2] VehicleTracker.update_tracks(vehicles)
       - track_id 별 경로(deque), 평균 신뢰도, path_length, 속도 히스토리 갱신
       - max_disappeared 초과 트랙 비활성화, 주기적으로 오래된 트랙 GC
   │
   ▼
[3] LaneManager.get_vehicle_lane(center) → lane_idx
       LaneManager.check_line_crossing(prev_y, curr_y, lane_idx) → 'up' | 'down' | None
   │
   ▼
[4] VehicleCounter.process_vehicle_crossing(vehicle, lane_idx, direction, history)
       - 중복 방지: (track_id, lane_idx, direction) 키로 Set 관리
       - min_track_length / confidence_threshold / directions 검증 통과 시에만 카운트
       - total / lane / direction / hourly 카운트와 이벤트 로그에 기록
   │
   ▼
[5] VehicleVisualizer.create_dashboard_frame(frame, vehicles, lane_manager, counter, tracker)
       - 차선·바운딩박스·추적경로·통계 패널을 오버레이
   │
   ▼
결과 프레임 (cv2.imshow 또는 VideoWriter 로 출력)
```

### 3.1 설정 우선순위

1. CLI 인자(`--model`, `--conf`, `--lanes`, `--input`, `--output` 등)
2. `config.yaml` (기본)
3. 내부 하드코드 기본값 (`_get_default_config`)

API 서버는 `JobOptions` → `pipeline._build_override()` → `system.update_config()` 경로로 동일 config 스키마를 덮어쓴다.

### 3.2 진행률 콜백

- `VehicleCountingSystem.progress_callback: Callable[[float, int, int], None]`
- 매 20 프레임마다 `(ratio, current_frame, total_frames)` 호출
- API 잡 실행기가 이 콜백을 이용해 `Job.progress` / `Job.current_frame` / `Job.total_frames` 를 갱신 → 프론트가 폴링으로 관찰

---

## 4. API 서버 (FastAPI)

### 4.1 구성

- `api/main.py` — `FastAPI` 앱 생성, CORS(`localhost:5173`) 허용, `/static` 에 `outputs/` 마운트
- `api/routes/jobs.py` — 업로드/목록/상세
- `api/routes/config.py` — `config.yaml` 읽기 전용 노출
- `api/jobs.py` — **in-memory `JobRegistry`** + 단일 워커 `ThreadPoolExecutor(max_workers=1)`
- `api/pipeline.py` — `run_pipeline()` 으로 `VehicleCountingSystem` 을 감싸고 결과 경로 규약화

### 4.2 엔드포인트

| 메소드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/api/health` | `{ status, gpu, version }` — torch.cuda 가용 시 GPU 이름 포함 |
| `POST` | `/api/jobs` | multipart: `file` + 선택(`lanes`,`confidence_threshold`,`model_path`) → `Job(queued)` |
| `GET` | `/api/jobs` | 최신순 잡 목록 |
| `GET` | `/api/jobs/{id}` | 단일 잡 상세 (진행률/결과/오류) |
| `GET` | `/api/config` | `config.yaml` 전체 |
| `GET` | `/static/{job_id}/result.mp4` 등 | 잡별 산출물 정적 서빙 |

### 4.3 잡 라이프사이클

```
queued ──────▶ running ──────▶ done
                    │              
                    └─────▶ error  (예외 포착 시)
```

- **queued**: `JobRegistry.create()` + 업로드 파일을 `backend/uploads/{job_id}.{ext}` 로 저장 후 `executor.submit(_run, ...)`
- **running**: `_run` 이 진입하면 status 갱신 + `progress_cb` 주입
- **done**: `run_pipeline` 반환값(artifacts/summary/total_counts/session)을 `Job.result` 에 저장, `progress=1.0`
- **error**: 예외 메시지를 `Job.error` 에 저장

### 4.4 결과물 경로 규약

`outputs/{job_id}/` 하위:

- `result.mp4` — 브라우저 재생용. OpenCV(avc1 우선 → mp4v fallback) 로 `result_raw.mp4` 생성 후, ffmpeg 가 있으면 libx264 + faststart 로 재인코딩하여 `result.mp4` 로 교체
- `results.json` — `VehicleCounter.export_results()` 산출 (총/차선/방향/시간별 카운트 + 이벤트 로그)
- `results_chart.png` — 차량 타입 원형차트 + 차선 막대차트
- `results_hourly.png` — 시간별 스택 바 차트

`Job.result.artifacts` 는 이들을 `/static/{job_id}/...` 상대경로로 노출한다.

### 4.5 MVP 제약 (의도적 단순화)

- **영속화 없음**: 재시작 시 잡 이력 소실 (in-memory dict). 운영 전 단계라 PG/SQLite 로의 교체 지점을 `JobRegistry` 에 국한해 둠.
- **단일 워커**: 단일 GPU 가정, 경합 방지를 위해 `max_workers=1`.
- **config 쓰기 불가**: `GET /api/config` 만 존재.
- **인증 없음**: CORS 는 개발용 `localhost:5173` 에 한정.

---

## 5. 프론트엔드 (Vue 3 SPA)

### 5.1 스택

- Vue 3 (Composition API, `<script setup>`)
- Vite 5 + `vue-tsc`
- Pinia 2 (jobs store)
- Vue Router 4 (`createWebHistory`)
- axios (`/api` 는 Vite dev 프록시로 `127.0.0.1:8000` 포워딩)

### 5.2 라우트

| 경로 | 컴포넌트 | 역할 |
|---|---|---|
| `/` | `HomeView.vue` | 헬스 표시, 업로드 폼, 잡 목록 테이블 + 3초 폴링(진행 중 잡이 있을 때만) |
| `/jobs/:id` | `JobView.vue` | 잡 상세 + 결과 영상/차트/카운트 요약. 상태에 따라 1s(running)/2s(queued) 폴링, done/error 시 정지 |

### 5.3 상태 관리

- `useJobsStore`: `jobs`, `loading`, `error`, `refresh()`, `create()`, `fetchOne()` 만 노출
- 상세 페이지(`JobView`)는 스토어 대신 `getJob()` 을 직접 호출 — 단일 리소스 폴링이 스토어 목록과 섞이지 않도록 분리

### 5.4 타입 동기화

`frontend/src/types/index.ts` 는 `backend/api/schemas.py` 의 Pydantic 모델을 **수작업 미러링**한다. 스키마 변경 시 양쪽을 함께 수정해야 한다.

---

## 6. 데이터 흐름 — 업로드에서 결과 재생까지

```
[브라우저 / HomeView]
  ├─ 파일 선택 + lanes/confidence 입력
  ├─ POST /api/jobs  (multipart)
  │     └─▶ FastAPI routes/jobs.create_job
  │            ├─ 확장자 / 숫자 범위 검증
  │            ├─ JobRegistry.create(filename, options)   → Job(queued)
  │            ├─ uploads/{job_id}.{ext} 로 스트림 저장 (aiofiles)
  │            └─ executor.submit(JobRegistry._run, job_id, path)
  └─ 응답: Job(queued) → router.push('/jobs/:id')

[워커 스레드 / JobRegistry._run]
  ├─ status=running, started_at=now
  ├─ progress_cb = ratio/current/total → Job 필드 갱신
  └─ run_pipeline(input, outputs/{id}, options, cb)
         ├─ VehicleCountingSystem(config.yaml)
         ├─ update_config(_build_override(...))  # lanes/conf/model_path 주입
         ├─ process_video() → result_raw.mp4 + results.json + 차트 PNG
         ├─ ffmpeg 로 H.264 재인코딩 → result.mp4
         └─ artifacts dict 반환
  └─ status=done, result=..., progress=1.0  (예외 시 status=error, error=str(exc))

[브라우저 / JobView]
  └─ 1s(running) / 2s(queued) 간격 polling GET /api/jobs/{id}
       ├─ running: <progress> 갱신
       ├─ done:    <video src="/static/{id}/result.mp4"> + <img src="/static/{id}/results_chart.png">
       └─ error:   오류 메시지 표시
```

---

## 7. 배포 토폴로지 (개발용)

```
┌────────────────────┐         ┌─────────────────────────────┐
│ Browser            │         │ Backend host                │
│ (localhost:5173)   │         │                             │
│                    │  HTTP   │  uvicorn api.main:app       │
│  Vue 3 SPA         │ ──────▶ │   ├─ :8000 /api/*           │
│  ─ axios / fetch   │         │   └─ :8000 /static/* (mount)│
│                    │         │                             │
│  vite dev proxy:   │         │  ThreadPoolExecutor (1)     │
│   /api → :8000     │         │   └─ VehicleCountingSystem  │
│   /static → :8000  │         │        └─ YOLOv8 (torch)    │
└────────────────────┘         │  uploads/  outputs/          │
                               └─────────────────────────────┘
```

프로덕션 시 고려할 지점(미구현):

- 잡 레지스트리 영속화 (SQLite/PostgreSQL, 혹은 Redis + RQ/Celery)
- 오브젝트 스토리지(S3 등)로 `outputs/` 오프로드
- 인증/인가 (현재 CORS 단일 오리진)
- 프론트 빌드 산출물(`vite build`)을 정적 서버 또는 CDN 으로 서빙
- ffmpeg 를 컨테이너 베이스 이미지에 포함

---

## 8. 확장 지점

| 영역 | 변경 지점 | 예시 |
|---|---|---|
| 감지 클래스 추가 | `VehicleDetector.vehicle_classes` | bicycle(1), train(6) 등 COCO 클래스 매핑 |
| 대각선/곡선 차선 | `LaneManager.setup_diagonal_lanes` (현재 스텁) | 폴리곤 기반 차선 정의 + 점-다각형 테스트 |
| 새 통계/리포트 | `VehicleCounter.get_*` + `VehicleVisualizer.create_*` | 주간 분석, 혼잡도 heatmap(실제 데이터 연결 필요) |
| 입력 소스 | `main_system.py` 의 `process_*` 계열 | RTSP 스트림, 이미지 시퀀스 |
| 잡 영속화 | `JobRegistry` 구현 교체 | SQLAlchemy + Alembic + 마이그레이션 |
| 실시간 진행률 | `/api/jobs/{id}` 폴링 → WS/SSE | FastAPI WebSocket 으로 push |

---

## 9. 주요 설계 트레이드오프

- **In-memory 잡 레지스트리**: MVP 속도 우선. 영속화를 덧붙이기 쉬운 경계(`JobRegistry` 단일 클래스)에 국한.
- **단일 워커**: GPU 경합/VRAM 초과 방지. 병렬화는 모델 인스턴스 풀 + `max_workers=N` 으로 쉽게 확장 가능.
- **OpenCV 인코딩 + 선택적 ffmpeg**: avc1 코덱이 없는 빌드에서도 동작하도록 mp4v fallback → ffmpeg 로 재인코딩해 브라우저 호환성 확보.
- **타입 수동 동기화**: OpenAPI 자동 생성 대신 수작업으로 최소한의 타입만 유지 → 의존성 체인을 얇게 유지, 스키마 드리프트는 PR 리뷰에서 검출.
- **차선 모드 auto/custom 만 지원**: 수평 차선이 다수 유스케이스를 커버. 대각선/폴리곤은 확장 지점으로 남김.
