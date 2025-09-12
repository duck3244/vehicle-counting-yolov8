# 🚗 YOLOv8 차선별 차량 카운팅 시스템

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Latest-green.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.5+-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**YOLOv8을 사용한 고성능 실시간 차선별 차량 감지, 추적 및 카운팅 시스템**

![Demo](https://via.placeholder.com/800x400/0066cc/ffffff?text=YOLOv8+Vehicle+Counting+Demo)

## 📋 목차

- [✨ 주요 기능](#-주요-기능)
- [🚀 빠른 시작](#-빠른-시작)
- [📁 프로젝트 구조](#-프로젝트-구조)
- [⚙️ 설치 방법](#️-설치-방법)
- [💻 사용법](#-사용법)
- [🎯 사용 예제](#-사용-예제)
- [⚡ 성능 최적화](#-성능-최적화)
- [🔧 커스터마이징](#-커스터마이징)
- [📊 출력 결과](#-출력-결과)
- [🔧 문제 해결](#-문제-해결)

## ✨ 주요 기능

### 🎯 **정확한 차량 감지 및 추적**
- **YOLOv8 최신 모델** 지원 (nano, small, medium, large, xlarge)
- **실시간 차량 추적** with 고유 ID 시스템
- **다양한 차량 타입** 분류 (승용차, 트럭, 버스, 오토바이)
- **고정밀 바운딩 박스** 및 신뢰도 기반 필터링

### 🛣️ **유연한 차선 관리**
- **자동 차선 설정** (균등 분할)
- **사용자 정의 차선** (좌표 기반 정밀 설정)
- **차선 검증** 시스템 (설정 오류 자동 감지)
- **다중 차선 지원** (2~10개 차선)

### 📊 **스마트 카운팅 시스템**
- **중복 방지** 카운팅 (동일 차량 재카운팅 방지)
- **방향별 카운팅** (상행/하행/양방향 선택)
- **실시간 통계** (시간별, 차선별, 타입별)
- **이벤트 로깅** (모든 카운팅 기록 저장)

### 🎨 **풍부한 시각화**
- **실시간 대시보드** (모든 정보 통합 표시)
- **추적 경로 시각화** (차량 이동 궤적)
- **다양한 차트** (원형, 막대, 히트맵)
- **전문 리포트** (HTML, JSON, CSV)

### ⚡ **고성능 처리**
- **GPU 가속** 지원 (CUDA 자동 감지)
- **멀티스레딩** 최적화
- **메모리 효율성** (대용량 비디오 처리)
- **실시간 스트리밍** (웹캠, IP 카메라)

## 🚀 빠른 시작

### ⚡ 즉시 실행
```bash
# 비디오 파일 처리
python main_system.py --input your_video.mp4 --output result.mp4

# 웹캠 실시간 처리
python main_system.py --webcam

# 대화형 예제 실행
python run_examples.py
```

## 📁 프로젝트 구조

```
vehicle-counting-yolov8/
├── 📋 README.md                    # 프로젝트 설명서
├── ⚙️ requirements.txt            # 패키지 의존성
├── 🔧 config.yaml                 # 설정 파일
│
├── 🧠 핵심 모듈/
│   ├── detector.py               # YOLOv8 차량 감지
│   ├── tracker.py                # 차량 추적 및 속도 계산
│   ├── lane_manager.py           # 차선 관리 및 검증
│   ├── counter.py                # 카운팅 로직 및 통계
│   └── visualizer.py             # 시각화 및 차트 생성
│
├── 🎯 메인 시스템/
│   ├── main_system.py            # 통합 시스템
│   └── run_examples.py           # 7가지 실행 예제
│
└── 📊 출력 파일/
    ├── counting_results.json     # 카운팅 결과 (JSON)
    ├── counting_chart.png        # 통계 차트
    └── report.html               # HTML 리포트
```

## ⚙️ 설치 방법

### 📋 시스템 요구사항
- **Python**: 3.7 이상
- **RAM**: 최소 8GB (권장 16GB)
- **GPU**: CUDA 지원 GPU (선택사항, 성능 향상)
- **디스크**: 최소 5GB 여유 공간

### 🔧 수동 설치 (고급 사용자)

#### 1. Python 환경 설정
```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 패키지 업그레이드
pip install --upgrade pip setuptools wheel
```

#### 2. 의존성 설치
```bash
# 모든 패키지 설치
pip install -r requirements.txt

# 또는 개별 설치
pip install ultralytics opencv-python numpy pillow pyyaml
pip install matplotlib seaborn pandas scipy
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### 3. YOLO 모델 다운로드
```bash
# 모델 디렉토리 생성
mkdir models

# 모델 다운로드 (선택)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt -O models/yolov8s.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt -O models/yolov8m.pt
```

#### 4. 디렉토리 구조 생성
```bash
mkdir -p {input_videos,output_videos,results,detected_vehicles,debug_frames}
```

## 💻 사용법

### 🎮 기본 명령어

```bash
# 기본 비디오 처리
python main_system.py --input video.mp4

# 출력 파일 지정
python main_system.py --input video.mp4 --output result.mp4

# 특정 모델 사용
python main_system.py --input video.mp4 --model yolov8m.pt

# 신뢰도 임계값 설정
python main_system.py --input video.mp4 --conf 0.7

# 차선 수 지정
python main_system.py --input video.mp4 --lanes 4

# 웹캠 사용
python main_system.py --webcam

# 화면 표시 없이 처리
python main_system.py --input video.mp4 --no-display

# 결과 저장
python main_system.py --input video.mp4 --save-results

# 설정 파일 사용
python main_system.py --config custom_config.yaml
```

### ⚙️ 설정 파일 사용

`config.yaml` 파일을 편집하여 상세 설정:

```yaml
# 모델 설정
model:
  path: "yolov8n.pt"
  confidence_threshold: 0.5
  device: "auto"  # auto, cpu, cuda

# 차선 설정
lanes:
  mode: "auto"  # auto, custom
  count: 3
  custom_lanes:
    - [0, 240]
    - [240, 480] 
    - [480, 720]

# 카운팅 설정
counting:
  directions: ["both"]  # up, down, both
  min_track_length: 5
  confidence_threshold: 0.5

# 비디오 설정
video:
  display_realtime: true
  save_output: true
  frame_skip: 1

# 출력 설정
output:
  save_results: true
  save_format: "json"
  save_cropped_vehicles: false
```

### 🐍 Python 스크립트에서 사용

```python
from main_system import VehicleCountingSystem

# 시스템 초기화
system = VehicleCountingSystem("config.yaml")

# 설정 커스터마이징
custom_config = {
    'model': {'path': 'yolov8s.pt', 'confidence_threshold': 0.6},
    'lanes': {'mode': 'auto', 'count': 4},
    'counting': {'directions': ['both']}
}
system.update_config(custom_config)

# 비디오 처리
success = system.process_video("input.mp4", "output.mp4")

# 웹캠 처리
# success = system.process_webcam()

# 시스템 상태 확인
status = system.get_system_status()
print(f"처리된 프레임: {status['frame_count']}")
print(f"총 차량 수: {status['total_vehicles']}")
```

## 🎯 사용 예제

### 📝 대화형 예제 실행

```bash
python run_examples.py
```

**7가지 예제 시나리오:**

1. **기본 비디오 처리** - 표준 3차선 도로 분석
2. **고정밀도 처리** - 큰 모델로 정확도 극대화  
3. **사용자 정의 차선** - 복잡한 차선 구조 설정
4. **웹캠 실시간 처리** - 라이브 스트리밍 분석
5. **일괄 처리** - 여러 비디오 자동 처리
6. **성능 비교** - 다양한 모델 벤치마크
7. **다양한 설정 시연** - 상황별 최적 설정

### 🎬 실제 사용 사례

#### 고속도로 교통량 분석
```bash
python main_system.py \
  --input highway_traffic.mp4 \
  --output highway_analysis.mp4 \
  --model yolov8m.pt \
  --lanes 5 \
  --conf 0.7 \
  --save-results
```

#### 도심 교차로 모니터링
```bash
python main_system.py \
  --input intersection.mp4 \
  --output intersection_result.mp4 \
  --model yolov8s.pt \
  --lanes 3 \
  --conf 0.6
```

#### 주차장 입구 카운팅
```yaml
# parking_config.yaml
lanes:
  mode: "custom"
  custom_lanes: [[200, 400]]  # 단일 차선

counting:
  directions: ["up"]  # 입장 차량만 카운팅
  min_track_length: 3
```

```bash
python main_system.py --config parking_config.yaml --input parking_entrance.mp4
```

## ⚡ 성능 최적화

### 🚀 **속도 최적화**

```yaml
# 고속 처리 설정
model:
  path: "yolov8n.pt"  # 가장 빠른 모델
  confidence_threshold: 0.4

video:
  frame_skip: 2  # 매 2프레임마다 처리

tracking:
  max_history_length: 20  # 짧은 히스토리
  max_disappeared: 15
```

### 🎯 **정확도 최적화**

```yaml
# 고정밀도 설정
model:
  path: "yolov8x.pt"  # 가장 정확한 모델
  confidence_threshold: 0.8

counting:
  min_track_length: 10  # 더 긴 추적 필요
  confidence_threshold: 0.7

tracking:
  max_history_length: 100  # 긴 히스토리
```

### 💾 **메모리 최적화**

```yaml
performance:
  memory_limit: "4GB"
  cleanup_interval: 300  # 5분마다 정리
  
tracking:
  max_disappeared: 30  # 사라진 트랙 빨리 제거
```

### 🔥 **GPU 활용**

```bash
# CUDA 환경 확인
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# GPU 메모리 확인
nvidia-smi

# 특정 GPU 사용
export CUDA_VISIBLE_DEVICES=0
python main_system.py --input video.mp4
```

## 🔧 커스터마이징

### 🎨 새로운 차량 타입 추가

```python
# detector.py 수정
class VehicleDetector:
    def __init__(self, ...):
        self.vehicle_classes = {
            2: 'car',
            3: 'motorcycle', 
            5: 'bus',
            7: 'truck',
            # 새로운 클래스 추가
            1: 'bicycle',
            4: 'airplane',
            6: 'train'
        }
```

### 🎭 시각화 커스터마이징

```python
# visualizer.py 설정 수정
custom_config = {
    'colors': {
        'car': (0, 255, 0),          # 초록색
        'truck': (255, 0, 0),        # 빨간색  
        'bus': (0, 0, 255),          # 파란색
        'motorcycle': (255, 255, 0), # 노란색
        'bicycle': (255, 0, 255),    # 마젠타 (새로운 색상)
    },
    'line_thickness': {
        'bbox': 3,                   # 더 두꺼운 박스
        'track_history': 4           # 더 굵은 추적선
    }
}

visualizer = VehicleVisualizer(custom_config)
```

### 🔄 카운팅 로직 확장

```python
# counter.py 확장
class CustomVehicleCounter(VehicleCounter):
    def __init__(self):
        super().__init__()
        self.rush_hour_counts = defaultdict(int)
    
    def process_rush_hour_counting(self, vehicle, current_hour):
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            self.rush_hour_counts[vehicle['class_name']] += 1
    
    def get_rush_hour_stats(self):
        return dict(self.rush_hour_counts)
```

### 🌐 새로운 입력 소스 추가

```python
# main_system.py 확장
def process_rtsp_stream(self, rtsp_url: str):
    """RTSP 스트림 처리"""
    cap = cv2.VideoCapture(rtsp_url)
    # 스트림 처리 로직...

def process_image_sequence(self, image_dir: str):
    """이미지 시퀀스 처리"""
    images = sorted(glob.glob(os.path.join(image_dir, "*.jpg")))
    # 이미지 시퀀스 처리 로직...
```

## 📊 출력 결과

### 📄 JSON 결과 예시

```json
{
  "session_info": {
    "start_time": 1703123456.789,
    "duration_seconds": 3600.0,
    "count_directions": ["both"]
  },
  "total_counts": {
    "car": 1247,
    "truck": 89,
    "bus": 23,
    "motorcycle": 156
  },
  "lane_counts": {
    "lane_1": {
      "car": 445,
      "truck": 32,
      "bus": 8,
      "motorcycle": 67
    },
    "lane_2": {
      "car": 398,
      "truck": 29,
      "bus": 7,
      "motorcycle": 45
    },
    "lane_3": {
      "car": 404,
      "truck": 28,
      "bus": 8,
      "motorcycle": 44
    }
  },
  "statistics": {
    "peak_hours": [
      ["08", 245],
      ["17", 289],
      ["18", 267]
    ],
    "lane_distribution": {
      "lane_1": 36.4,
      "lane_2": 31.6,
      "lane_3": 32.0
    },
    "vehicle_type_distribution": {
      "car": 82.4,
      "motorcycle": 10.3,
      "truck": 5.9,
      "bus": 1.5
    },
    "vehicles_per_hour": 421.8
  }
}
```

### 📈 생성되는 차트들

1. **원형 차트** (`counting_chart.png`)
   - 차량 타입별 분포 비율
   - 색상별 차량 구분
   
2. **막대 차트** (`lane_distribution.png`)  
   - 차선별 교통량 비교
   - 시간대별 분석

3. **시간별 차트** (`hourly_chart.png`)
   - 24시간 교통 패턴
   - 피크 시간대 식별

4. **히트맵** (`traffic_heatmap.png`)
   - 차선-시간 교차 분석
   - 핫스팟 지역 식별

### 🌐 HTML 리포트

자동 생성되는 전문적인 HTML 리포트에는 다음이 포함됩니다:

- 📊 **종합 통계 대시보드**
- 🎯 **차량 타입별 상세 분석** 
- 🛣️ **차선별 교통 패턴**
- ⏰ **시간대별 트렌드 분석**
- 📈 **모든 차트 통합 표시**
- 📋 **설정 및 메타데이터**

## 🔧 문제 해결

### ❗ 일반적인 문제들

#### 1. **YOLOv8 모델 다운로드 실패**

```bash
# 해결 방법 1: 수동 다운로드
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
mv yolov8n.pt models/

# 해결 방법 2: Python으로 다운로드
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

#### 2. **CUDA/GPU 관련 오류**

```bash
# CPU 모드로 강제 실행
export CUDA_VISIBLE_DEVICES=""
python main_system.py --input video.mp4

# 또는 config.yaml에서 설정
model:
  device: "cpu"
```

#### 3. **메모리 부족 오류**

```bash
# 더 작은 모델 사용
python main_system.py --input video.mp4 --model yolov8n.pt

# 프레임 건너뛰기로 메모리 절약
# config.yaml에서:
video:
  frame_skip: 3  # 매 3프레임마다 처리
```

#### 4. **OpenCV 관련 오류**

```bash
# OpenCV 재설치
pip uninstall opencv-python opencv-python-headless
pip install opencv-python

# 헤드리스 버전 (서버 환경)
pip install opencv-python-headless
```

#### 5. **느린 처리 속도**

```yaml
# 성능 최적화 설정
model:
  path: "yolov8n.pt"  # 가장 빠른 모델
  confidence_threshold: 0.6  # 높은 임계값으로 연산 줄이기

video:
  frame_skip: 2  # 프레임 건너뛰기

tracking:
  max_history_length: 20  # 짧은 히스토리
```

### 🔍 디버깅 모드

```bash
# 상세 로그와 함께 실행
python main_system.py --input video.mp4 --config debug_config.yaml

# debug_config.yaml:
debug:
  log_level: "DEBUG"
  save_debug_frames: true
  verbose: true
```

### 📞 도움말 확인

```bash
# 사용 가능한 모든 옵션 보기
python main_system.py --help

# 예제 도움말
python run_examples.py --help
``` 

---