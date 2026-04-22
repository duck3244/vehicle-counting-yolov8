# UML 다이어그램 — Vehicle Counting YOLOv8

본 문서는 프로젝트의 정적/동적 구조를 Mermaid 기반 UML 로 정리한 것이다. 전반 아키텍처 설명은 [`architecture.md`](./architecture.md) 를 참고한다.

수록된 다이어그램:

1. [컴포넌트 다이어그램](#1-컴포넌트-다이어그램) — 시스템 전체 구성 요소와 관계
2. [클래스 다이어그램 (backend core)](#2-클래스-다이어그램--backend-core) — 파이프라인 5 클래스 + 오케스트레이터
3. [클래스 다이어그램 (api layer)](#3-클래스-다이어그램--api-layer) — FastAPI 어댑터 + Pydantic 모델
4. [클래스 다이어그램 (frontend)](#4-클래스-다이어그램--frontend) — Vue/Pinia 컴포넌트 + 타입
5. [시퀀스 다이어그램 — 잡 제출에서 완료까지](#5-시퀀스-다이어그램--잡-제출에서-완료까지)
6. [시퀀스 다이어그램 — 프레임 처리 루프](#6-시퀀스-다이어그램--프레임-처리-루프)
7. [상태 다이어그램 — 잡 라이프사이클](#7-상태-다이어그램--잡-라이프사이클)
8. [상태 다이어그램 — Track 라이프사이클](#8-상태-다이어그램--track-라이프사이클)

---

## 1. 컴포넌트 다이어그램

```mermaid
flowchart LR
    subgraph Browser["Browser (localhost:5173)"]
        SPA["Vue 3 SPA<br/>(HomeView / JobView)"]
        Store["Pinia jobs store"]
        AxiosC["axios client<br/>(/api, /static)"]
        SPA --> Store
        SPA --> AxiosC
        Store --> AxiosC
    end

    subgraph Vite["Vite dev server"]
        Proxy["/api, /static proxy"]
    end

    subgraph Backend["Backend (uvicorn :8000)"]
        API["FastAPI app<br/>(api.main)"]
        RoutesJ["routes/jobs.py"]
        RoutesC["routes/config.py"]
        Registry["JobRegistry<br/>(in-memory)"]
        Executor["ThreadPoolExecutor<br/>(max_workers=1)"]
        Pipeline["pipeline.run_pipeline"]
        VCS["VehicleCountingSystem"]
        subgraph Core["Core modules"]
            Det["VehicleDetector<br/>(YOLOv8)"]
            Trk["VehicleTracker"]
            Lane["LaneManager"]
            Cnt["VehicleCounter"]
            Viz["VehicleVisualizer"]
        end
        Static["StaticFiles mount<br/>/static → outputs/"]
        FFmpeg["ffmpeg<br/>(H.264 재인코딩)"]

        API --> RoutesJ
        API --> RoutesC
        API --> Static
        RoutesJ --> Registry
        Registry --> Executor
        Executor --> Pipeline
        Pipeline --> VCS
        Pipeline --> FFmpeg
        VCS --> Det
        VCS --> Trk
        VCS --> Lane
        VCS --> Cnt
        VCS --> Viz
    end

    subgraph FS["File system"]
        UP["uploads/"]
        OUT["outputs/{job_id}/"]
        CFG["config.yaml"]
    end

    AxiosC -->|http| Proxy
    Proxy --> API
    RoutesJ -->|save| UP
    Pipeline -->|write| OUT
    Static -.serve.-> OUT
    RoutesC -->|read| CFG
    VCS -->|load| CFG
```

---

## 2. 클래스 다이어그램 — backend core

`backend/` 의 파이프라인 5 클래스와 오케스트레이터 `VehicleCountingSystem`.

```mermaid
classDiagram
    class VehicleCountingSystem {
        +Dict config
        +Path config_path
        +VehicleDetector detector
        +VehicleTracker tracker
        +LaneManager lane_manager
        +VehicleCounter counter
        +VehicleVisualizer visualizer
        +bool is_running
        +int frame_count
        +deque fps_counter
        +deque processing_times
        +Callable progress_callback
        +__init__(config_path)
        +initialize_modules(w, h)
        +process_frame(frame) ndarray
        +process_video(input, output) bool
        +process_webcam(camera_index) bool
        +update_config(new_config)
        +get_system_status() Dict
        +stop_processing()
        -_load_config(path) Dict
        -_setup_logging()
        -_setup_lanes()
        -_open_video_writer(path, fps, w, h) VideoWriter
        -_save_results()
        -_print_final_results()
    }

    class VehicleDetector {
        +str model_path
        +float conf_threshold
        +str device
        +Dict vehicle_classes
        +YOLO model
        +Dict detection_stats
        +detect_vehicles(frame, track) List~Dict~
        +filter_by_size(vehicles, min, max) List~Dict~
        +filter_by_region(vehicles, region) List~Dict~
        +get_vehicle_crops(frame, vehicles) List
        +draw_detections(frame, vehicles, ...) ndarray
        +update_confidence_threshold(t)
        +get_model_info() Dict
        +get_detection_stats() Dict
        +reset_stats()
        -_load_model() YOLO
        -_process_results(results) List~Dict~
    }

    class VehicleTracker {
        +int max_history_length
        +int max_disappeared
        +int cleanup_interval_frames
        +float cleanup_max_age_seconds
        +Dict tracks
        +defaultdict~deque~ track_history
        +defaultdict disappeared_counts
        +Dict stats
        +update_tracks(vehicles) List~Dict~
        +get_track_history(track_id, max) List
        +calculate_speed(track_id, fps, ppm) float
        +get_average_speed(track_id) float
        +draw_tracks(frame, vehicles, ...) ndarray
        +get_active_tracks() List~int~
        +get_track_info(track_id) Dict
        +cleanup_old_tracks(max_age)
        +export_track_data(track_id) Dict
        +reset()
        -_create_new_track(id, vehicle)
        -_update_track(id, vehicle)
        -_handle_disappeared_tracks(current_ids)
    }

    class LaneManager {
        +int frame_width
        +int frame_height
        +List~Tuple~ lanes
        +List~int~ counting_lines
        +List~str~ lane_names
        +Dict colors
        +Dict line_thickness
        +setup_auto_lanes(n, mt, mb) bool
        +setup_custom_lanes(configs) bool
        +get_vehicle_lane(center) int
        +get_vehicle_lane_info(center) Dict
        +check_line_crossing(prev_y, curr_y, lane_idx) str
        +draw_lanes(frame, ...) ndarray
        +draw_roi(frame, roi) ndarray
        +get_lane_stats() Dict
        +export_config(filename)
        +import_config(filename) bool
        +update_frame_size(w, h)
        +get_lane_polygons() List
        +reset()
        -_validate_lane_configs(configs) bool
    }

    class VehicleCounter {
        +List~str~ count_directions
        +defaultdict total_counts
        +defaultdict lane_counts
        +defaultdict direction_counts
        +defaultdict hourly_counts
        +Set crossed_vehicles
        +List counting_events
        +int min_track_length
        +float confidence_threshold
        +float counting_session_start
        +process_vehicle_crossing(vehicle, lane, dir, history) bool
        +get_total_counts() Dict
        +get_lane_counts() Dict
        +get_direction_counts() Dict
        +get_hourly_counts() Dict
        +get_counting_rate(window) Dict
        +get_peak_hours() List
        +get_lane_distribution() Dict
        +get_vehicle_type_distribution() Dict
        +get_counting_statistics() Dict
        +get_summary_report() str
        +draw_counting_info(frame, pos) ndarray
        +draw_lane_counts(frame, positions) ndarray
        +export_results(filename, output_dir)
        +import_results(filename) bool
        +set_counting_parameters(...)
        +reset_counts()
        -_validate_counting_conditions(...) bool
        -_execute_counting(...)
        -_log_counting_event(...)
    }

    class VehicleVisualizer {
        +Dict config
        +draw_vehicles(frame, vehicles) ndarray
        +draw_lanes(frame, lane_manager) ndarray
        +draw_statistics_panel(frame, counter, pos) ndarray
        +draw_speed_info(frame, vehicle, tracker) ndarray
        +draw_counting_zones(frame, lane_manager) ndarray
        +create_dashboard_frame(frame, vehicles, lm, ct, tr) ndarray
        +create_counting_chart(counter, save_path) Figure
        +create_hourly_chart(counter, save_path) Figure
        +create_heatmap(counter, save_path) Figure
        +create_summary_video_frame(counter, size) ndarray
        +create_comparison_frame(frames, labels) ndarray
        +save_visualization_config(filename)
        +load_visualization_config(filename) bool
        +update_display_settings(**kwargs)
        -_update_config(config)
        -_draw_vehicle_bbox(frame, vehicle) ndarray
        -_draw_track_history(frame, vehicle) ndarray
        -_draw_direction_arrow(frame, p1, p2, color)
        -_draw_label(frame, text, pos, color)
        -_draw_total_counts(frame, counter, x, y) int
        -_draw_lane_counts(frame, counter, x, y) int
        -_draw_rates(frame, counter, x, y) int
        -_calculate_panel_height(counter) int
        -_get_matplotlib_color(vtype) str
        -_draw_frame_info(frame) ndarray
    }

    VehicleCountingSystem --> VehicleDetector : uses
    VehicleCountingSystem --> VehicleTracker : uses
    VehicleCountingSystem --> LaneManager : uses
    VehicleCountingSystem --> VehicleCounter : uses
    VehicleCountingSystem --> VehicleVisualizer : uses
    VehicleVisualizer ..> VehicleCounter : reads stats
    VehicleVisualizer ..> LaneManager : reads lanes
    VehicleVisualizer ..> VehicleTracker : reads speed
    VehicleCounter ..> LaneManager : lane_idx
```

---

## 3. 클래스 다이어그램 — api layer

FastAPI 어댑터와 Pydantic 모델. `backend/api/` 범위.

```mermaid
classDiagram
    class FastAPIApp {
        <<FastAPI>>
        +include_router(jobs_router)
        +include_router(config_router)
        +mount_static_outputs()
        +health() HealthResponse
    }

    class JobsRouter {
        <<APIRouter>>
        +create_job(file, lanes, conf, model_path) Job
        +list_jobs() List~Job~
        +get_job(id) Job
    }
    note for JobsRouter "prefix: /api/jobs\nPOST  — create_job\nGET   — list_jobs\nGET   :id — get_job"

    class ConfigRouter {
        <<APIRouter>>
        +get_config() dict
    }
    note for ConfigRouter "prefix: /api/config\nGET   — get_config"

    class JobRegistry {
        -Dict~str,Job~ _jobs
        -Lock _lock
        -ThreadPoolExecutor _executor
        +create(filename, options) Job
        +get(job_id) Job
        +list() List~Job~
        +submit(job_id, input_path)
        -_update(job_id, **kwargs)
        -_run(job_id, input_path)
    }

    class Pipeline {
        <<module>>
        +run_pipeline(input, output_dir, options, cb) Dict
        -_build_override(output_dir, options) Dict
        -_transcode_h264(src, dst) bool
    }

    class JobStatus {
        <<enum>>
        queued
        running
        done
        error
    }

    class JobOptions {
        <<Pydantic>>
        +int? lanes
        +float? confidence_threshold
        +str? model_path
    }

    class Job {
        <<Pydantic>>
        +str id
        +JobStatus status
        +str filename
        +datetime created_at
        +datetime? started_at
        +datetime? finished_at
        +float progress
        +int current_frame
        +int total_frames
        +str? message
        +JobOptions options
        +Dict? result
        +str? error
    }

    class HealthResponse {
        <<Pydantic>>
        +str status
        +str? gpu
        +str version
    }

    FastAPIApp --> JobsRouter
    FastAPIApp --> ConfigRouter
    FastAPIApp ..> HealthResponse : returns
    JobsRouter --> JobRegistry : uses
    JobsRouter ..> Job : returns
    JobsRouter ..> JobOptions : validates
    JobRegistry --> Pipeline : submits
    JobRegistry "1" *-- "*" Job
    Job --> JobStatus
    Job --> JobOptions
    Pipeline ..> VehicleCountingSystem : delegates
    Pipeline ..> ffmpeg : optional

    class VehicleCountingSystem {
        <<imported>>
    }
    class ffmpeg {
        <<external>>
    }
```

---

## 4. 클래스 다이어그램 — frontend

`frontend/src/` 의 Vue 컴포넌트, Pinia 스토어, axios 클라이언트, TS 타입.

```mermaid
classDiagram
    class AppVue {
        <<VueSFC>>
        RouterLink
        RouterView
    }

    class Router {
        <<vue-router>>
        +routes
    }
    note for Router "routes:\n  path=/            → HomeView\n  path=/jobs/:id    → JobView"

    class HomeView {
        <<VueSFC>>
        -Ref~Health~ health
        -Ref~File~ file
        -Ref~number~ lanes
        -Ref~number~ conf
        -Ref~boolean~ submitting
        -Ref~number~ uploadProgress
        +onFileChange(e)
        +submit()
        +badgeClass(job)
        +pct(job)
        onMounted: fetchHealth + store.refresh + setInterval(3s)
    }

    class JobView {
        <<VueSFC>>
        -Ref~Job~ job
        -Ref~string~ error
        +load()
        +scheduleNext()
        onMounted: load + schedule polling
    }

    class JobsStore {
        <<PiniaStore>>
        +Ref~Job[]~ jobs
        +Ref~boolean~ loading
        +Ref~string~ error
        +refresh() Promise
        +create(params) Promise~Job~
        +fetchOne(id) Promise~Job~
    }

    class ApiClient {
        <<module>>
        +fetchHealth() Health
        +listJobs() Job[]
        +getJob(id) Job
        +createJob(params) Job
    }

    class CreateJobParams {
        <<interface>>
        +File file
        +number? lanes
        +number? confidence_threshold
        +string? model_path
        +Function? onUploadProgress
    }

    class JobType {
        <<TSInterface>>
        +string id
        +JobStatus status
        +string filename
        +string created_at
        +string? started_at
        +string? finished_at
        +number progress
        +number current_frame
        +number total_frames
        +string? message
        +JobOptions options
        +JobResult? result
        +string? error
    }

    class JobStatusT {
        <<TSUnion>>
        queued | running | done | error
    }

    class JobOptionsT {
        <<TSInterface>>
        +number? lanes
        +number? confidence_threshold
        +string? model_path
    }

    class JobResult {
        <<TSInterface>>
        +JobResultArtifacts artifacts
        +Record total_counts
        +Record summary
        +Record session
    }

    class Health {
        <<TSInterface>>
        +string status
        +string? gpu
        +string version
    }

    AppVue --> Router
    Router --> HomeView
    Router --> JobView
    HomeView --> JobsStore
    HomeView --> ApiClient : fetchHealth
    JobView --> ApiClient : getJob
    JobsStore --> ApiClient : list/create/get
    ApiClient ..> CreateJobParams
    ApiClient ..> JobType : typed
    ApiClient ..> Health : typed
    JobType --> JobStatusT
    JobType --> JobOptionsT
    JobType --> JobResult
```

---

## 5. 시퀀스 다이어그램 — 잡 제출에서 완료까지

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant Home as HomeView.vue
    participant Store as Pinia jobs store
    participant Ax as axios client
    participant Api as FastAPI (api.main)
    participant Route as routes/jobs.py
    participant Reg as JobRegistry
    participant Exe as ThreadPoolExecutor
    participant Pipe as pipeline.run_pipeline
    participant VCS as VehicleCountingSystem
    participant FS as filesystem
    participant FF as ffmpeg
    participant Job as JobView.vue

    User->>Home: 파일 선택 + 옵션 입력 + 제출
    Home->>Store: store.create(params)
    Store->>Ax: POST /api/jobs (multipart)
    Ax->>Api: HTTP
    Api->>Route: create_job()
    Route->>Route: 확장자/범위 검증
    Route->>Reg: create(filename, options)
    Reg-->>Route: Job(queued)
    Route->>FS: uploads/{id}.{ext} 저장 (aiofiles)
    Route->>Reg: submit(id, path)
    Reg->>Exe: executor.submit(_run, ...)
    Route-->>Ax: 201 Job(queued)
    Ax-->>Store: Job
    Store-->>Home: Job
    Home->>Job: router.push /jobs/{id}

    par 워커 처리
        Exe->>Reg: _run(job_id, path)
        Reg->>Reg: status=running, started_at=now
        Reg->>Pipe: run_pipeline(input, outputs/{id}, options, cb)
        Pipe->>VCS: VehicleCountingSystem(config.yaml)
        Pipe->>VCS: update_config(override)
        Pipe->>VCS: process_video()
        loop 매 프레임
            VCS->>VCS: detect → track → lane → count → viz
            VCS-->>Reg: progress_cb(ratio, cur, total)
            Reg->>Reg: _update(progress, current_frame, total_frames)
        end
        VCS->>FS: result_raw.mp4 + results.json + chart.png
        Pipe->>FF: libx264 재인코딩
        FF->>FS: result.mp4
        Pipe-->>Reg: artifacts + summary
        Reg->>Reg: status=done, result=..., progress=1.0
    and 프론트 폴링
        loop 1s/2s interval (status 에 따라)
            Job->>Ax: GET /api/jobs/{id}
            Ax->>Api: HTTP
            Api->>Route: get_job(id)
            Route->>Reg: get(id)
            Reg-->>Route: Job
            Route-->>Ax: Job
            Ax-->>Job: Job
            Job->>Job: <progress> 또는 결과 영상 렌더
        end
    end

    Note over Job,Api: status=done 시 폴링 종료.<br/>/static/{id}/result.mp4 를 <video> 로 재생
```

---

## 6. 시퀀스 다이어그램 — 프레임 처리 루프

`VehicleCountingSystem.process_frame()` 내부. 매 프레임당 5 단계.

```mermaid
sequenceDiagram
    autonumber
    participant V as process_video loop
    participant S as VehicleCountingSystem
    participant D as VehicleDetector
    participant T as VehicleTracker
    participant L as LaneManager
    participant C as VehicleCounter
    participant Z as VehicleVisualizer

    V->>S: process_frame(frame)
    S->>D: detect_vehicles(frame, track=True)
    D->>D: YOLO.track() + class/conf 필터
    D-->>S: vehicles[] (bbox/conf/track_id/center/area)

    S->>T: update_tracks(vehicles)
    T->>T: _create_new_track / _update_track / _handle_disappeared
    T->>T: (주기) cleanup_old_tracks()
    T-->>S: vehicles[] + track_info

    loop 각 vehicle
        S->>L: get_vehicle_lane(center) → lane_idx
        alt lane_idx >= 0
            S->>T: get_track_history(track_id)
            T-->>S: [(x,y), ...]
            S->>L: check_line_crossing(prev_y, curr_y, lane_idx)
            L-->>S: 'up' | 'down' | None
            alt 통과 감지
                S->>C: process_vehicle_crossing(vehicle, lane_idx, dir, history)
                C->>C: 중복키 체크 + min_track_length/conf 검증
                C->>C: total/lane/direction/hourly 카운트 갱신
                C-->>S: true/false
            end
        end
    end

    S->>Z: create_dashboard_frame(frame, vehicles, L, C, T)
    Z->>Z: draw_lanes + draw_vehicles + stats_panel + frame_info
    Z-->>S: result_frame
    S->>S: FPS/processing_time 기록
    S-->>V: result_frame
```

---

## 7. 상태 다이어그램 — 잡 라이프사이클

```mermaid
stateDiagram-v2
    [*] --> queued : POST /api/jobs\n(업로드 완료 + submit)
    queued --> running : executor 가 _run 진입\nstarted_at = now
    running --> running : progress_cb\nprogress/current_frame 갱신
    running --> done : run_pipeline 성공\nresult 저장, progress=1.0
    running --> error : 예외 포착\nerror 메시지 저장
    queued --> error : (미구현) 검증 실패 경로
    done --> [*]
    error --> [*]

    note right of running
      finished_at 은 done/error 시 기록.
      프론트는 done/error 에서 폴링 중지.
    end note
```

---

## 8. 상태 다이어그램 — Track 라이프사이클

`VehicleTracker` 내부 트랙 한 개의 상태.

```mermaid
stateDiagram-v2
    [*] --> active : _create_new_track\n(신규 track_id 등장)
    active --> active : _update_track\n(히스토리/신뢰도/path_length 갱신)
    active --> missing : current_track_ids 에 없음\ndisappeared_counts++
    missing --> active : 다시 감지됨\ndisappeared_counts = 0
    missing --> inactive : disappeared >= max_disappeared
    inactive --> [*] : cleanup_old_tracks\n(last_seen 이 max_age 초과)

    note right of inactive
      is_active=false.
      draw_tracks 대상에서 제외.
      GC 전까지 history 는 보존.
    end note
```

---

## 부록 — 다이어그램 렌더링

- GitHub, GitLab, VS Code Markdown Preview Enhanced, 대부분의 최신 IDE 에서 Mermaid 블록은 자동 렌더된다.
- 로컬 이미지로 추출하려면 `@mermaid-js/mermaid-cli` (`mmdc`) 사용:
  ```bash
  npx -p @mermaid-js/mermaid-cli mmdc -i docs/uml.md -o docs/uml.png
  ```
