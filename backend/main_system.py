"""
메인 시스템
모든 모듈을 통합한 차선별 차량 카운팅 시스템
"""

import cv2
import numpy as np
import argparse
import yaml
import logging
import time
from collections import deque
from pathlib import Path
from typing import Callable, Dict, List, Optional

ProgressCallback = Callable[[float, int, int], None]  # (progress 0~1, current, total)

# 모듈 임포트
from detector import VehicleDetector
from tracker import VehicleTracker
from lane_manager import LaneManager
from counter import VehicleCounter
from visualizer import VehicleVisualizer


class VehicleCountingSystem:
    """통합 차량 카운팅 시스템"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        시스템 초기화

        Args:
            config_path (str): 설정 파일 경로
        """
        # 설정 로드 (경로를 함께 보관하여 이후 백업 등에서 재사용)
        self.config_path: Optional[Path] = (
            Path(config_path).resolve() if Path(config_path).is_file() else None
        )
        self.config = self._load_config(config_path)
        
        # 로깅 설정
        self._setup_logging()
        
        # 모듈 초기화
        self.detector = None
        self.tracker = None
        self.lane_manager = None
        self.counter = None
        self.visualizer = None
        
        # 상태 변수
        self.is_running = False
        self.frame_count = 0
        self.start_time = None

        # 진행률 콜백 (API 서버 등 외부에서 주입 가능)
        self.progress_callback: Optional[ProgressCallback] = None
        
        # 성능 측정 (무한 증가 방지를 위해 고정 길이 deque 사용)
        self.fps_counter: deque = deque(maxlen=300)
        self.processing_times: deque = deque(maxlen=300)
        
        logging.info("VehicleCountingSystem 초기화 완료")
    
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            logging.warning(f"설정 파일을 찾을 수 없습니다: {config_path}")
            return self._get_default_config()
        except Exception as e:
            logging.error(f"설정 파일 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """기본 설정 반환"""
        return {
            'model': {
                'path': 'yolov8n.pt',
                'confidence_threshold': 0.5,
                'device': 'auto'
            },
            'lanes': {
                'mode': 'auto',
                'count': 3
            },
            'tracking': {
                'max_history_length': 50,
                'max_disappeared': 30
            },
            'counting': {
                'directions': ['both'],
                'min_track_length': 5,
                'confidence_threshold': 0.5
            },
            'video': {
                'input_path': None,
                'output_path': None,
                'display_realtime': True,
                'save_output': False
            },
            'visualization': {
                'show_bbox': True,
                'show_track_history': True,
                'show_lanes': True,
                'show_statistics': True
            },
            'output': {
                'save_results': True,
                'results_format': 'json',
                'results_file': 'counting_results'
            }
        }
    
    def _setup_logging(self):
        """로깅 설정

        같은 프로세스에서 여러 번 호출되어도 핸들러가 중복으로 추가되지 않도록
        ``force=True`` 로 루트 로거의 기존 핸들러를 제거한 뒤 재설정한다.
        API 서버 등 외부에서 이미 로깅을 구성한 경우 ``debug.skip_logging_setup``
        을 true 로 지정하면 이 함수는 아무 작업도 하지 않는다.
        """
        debug_cfg = self.config.get('debug', {})
        if debug_cfg.get('skip_logging_setup', False):
            return

        log_level = debug_cfg.get('log_level', 'INFO')
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_file = debug_cfg.get('log_file', 'vehicle_counting.log')

        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file),
            ],
            force=True,
        )
    
    def initialize_modules(self, frame_width: int = 1920, frame_height: int = 1080):
        """모듈들 초기화"""
        try:
            # 차량 감지기
            model_config = self.config.get('model', {})
            self.detector = VehicleDetector(
                model_path=model_config.get('path', 'yolov8n.pt'),
                conf_threshold=model_config.get('confidence_threshold', 0.5),
                device=model_config.get('device', 'auto')
            )
            
            # 차량 추적기
            tracking_config = self.config.get('tracking', {})
            self.tracker = VehicleTracker(
                max_history_length=tracking_config.get('max_history_length', 50),
                max_disappeared=tracking_config.get('max_disappeared', 30),
                cleanup_interval_frames=tracking_config.get('cleanup_interval_frames', 300),
                cleanup_max_age_seconds=tracking_config.get('cleanup_max_age_seconds', 300),
            )
            
            # 차선 관리자
            self.lane_manager = LaneManager(frame_width, frame_height)
            self._setup_lanes()
            
            # 카운터
            counting_config = self.config.get('counting', {})
            self.counter = VehicleCounter(
                count_directions=counting_config.get('directions', ['both'])
            )
            self.counter.set_counting_parameters(
                min_track_length=counting_config.get('min_track_length', 5),
                confidence_threshold=counting_config.get('confidence_threshold', 0.5)
            )
            
            # 시각화기
            viz_config = self.config.get('visualization', {})
            self.visualizer = VehicleVisualizer(viz_config)
            
            logging.info("모든 모듈 초기화 완료")
            
        except Exception as e:
            logging.error(f"모듈 초기화 실패: {e}")
            raise
    
    def _setup_lanes(self):
        """차선 설정"""
        lane_config = self.config.get('lanes', {})
        mode = lane_config.get('mode', 'auto')
        
        if mode == 'auto':
            count = lane_config.get('count', 3)
            margin_top = lane_config.get('margin_top', 50)
            margin_bottom = lane_config.get('margin_bottom', 50)
            
            success = self.lane_manager.setup_auto_lanes(count, margin_top, margin_bottom)
            if not success:
                raise ValueError("자동 차선 설정 실패")
                
        elif mode == 'custom':
            custom_lanes = lane_config.get('custom_lanes', [])
            if not custom_lanes:
                raise ValueError("사용자 정의 차선 설정이 비어있음")
            
            success = self.lane_manager.setup_custom_lanes(custom_lanes)
            if not success:
                raise ValueError("사용자 정의 차선 설정 실패")
        
        else:
            raise ValueError(f"지원되지 않는 차선 모드: {mode}")
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """단일 프레임 처리"""
        frame_start_time = time.time()
        
        try:
            # 1. 차량 감지 (추적 포함)
            vehicles = self.detector.detect_vehicles(frame, track=True)
            
            # 2. 추적 정보 업데이트
            vehicles = self.tracker.update_tracks(vehicles)
            
            # 3. 차선별 카운팅 처리
            for vehicle in vehicles:
                track_id = vehicle.get('track_id')
                if track_id is None:
                    continue
                
                # 차선 확인
                center = vehicle.get('center')
                if not center:
                    continue
                    
                lane_idx = self.lane_manager.get_vehicle_lane(center)
                if lane_idx == -1:
                    continue
                
                # 추적 히스토리에서 라인 통과 확인
                track_history = self.tracker.get_track_history(track_id)
                if len(track_history) >= 2:
                    prev_y = track_history[-2][1]
                    curr_y = track_history[-1][1]
                    
                    direction = self.lane_manager.check_line_crossing(prev_y, curr_y, lane_idx)
                    if direction:
                        # 카운팅 처리
                        self.counter.process_vehicle_crossing(
                            vehicle, lane_idx, direction, track_history
                        )
            
            # 4. 시각화
            if self.config.get('visualization', {}).get('enabled', True):
                # 차량 히스토리 정보 추가
                for vehicle in vehicles:
                    track_id = vehicle.get('track_id')
                    if track_id:
                        vehicle['track_history'] = self.tracker.get_track_history(track_id)
                
                # 통합 대시보드 프레임 생성
                result_frame = self.visualizer.create_dashboard_frame(
                    frame, vehicles, self.lane_manager, self.counter, self.tracker
                )
            else:
                result_frame = frame.copy()
            
            # 성능 측정
            processing_time = time.time() - frame_start_time
            self.processing_times.append(processing_time)
            
            # FPS 계산 (최근 30 프레임 평균 — deque 는 슬라이싱 미지원이라 list 변환)
            if len(self.processing_times) >= 30:
                recent = list(self.processing_times)[-30:]
                avg_time = sum(recent) / len(recent)
                fps = 1.0 / avg_time if avg_time > 0 else 0
                self.fps_counter.append(fps)
            
            self.frame_count += 1
            
            return result_frame
            
        except Exception as e:
            logging.error(f"프레임 처리 오류: {e}")
            return frame
    
    @staticmethod
    def _open_video_writer(output_path: str, fps: int,
                           width: int, height: int) -> Optional[cv2.VideoWriter]:
        """브라우저 호환을 위해 H.264(avc1) 우선 시도, 실패 시 mp4v 로 fallback.

        OpenCV 빌드에 H.264 코덱이 포함돼 있지 않으면 avc1 writer 는
        ``isOpened()`` 가 False 로 반환된다. 그 경우 조용히 mp4v 로 떨어뜨린다
        (경고는 남긴다).
        """
        for codec in ('avc1', 'mp4v'):
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if writer.isOpened():
                if codec != 'avc1':
                    logging.warning(
                        "H.264(avc1) 인코더가 없어 mp4v 로 저장합니다 — "
                        "브라우저에서 바로 재생되지 않을 수 있으니 ffmpeg 후처리를 권장합니다."
                    )
                logging.info(f"결과 영상 코덱: {codec}")
                return writer
            writer.release()
        return None

    def process_video(self, input_path: str, output_path: str = None) -> bool:
        """비디오 파일 처리"""
        if not Path(input_path).is_file():
            logging.error(f"입력 파일이 존재하지 않습니다: {input_path}")
            return False

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            logging.error(f"비디오 파일을 열 수 없습니다: {input_path}")
            return False

        # 비디오 속성 + 검증
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0 or fps <= 0:
            logging.error(
                f"비디오 메타데이터가 유효하지 않습니다: {width}x{height}, {fps}fps"
            )
            cap.release()
            return False
        if total_frames <= 0:
            logging.warning("총 프레임 수를 확인할 수 없습니다. 진행률은 표시되지 않습니다.")

        logging.info(f"비디오 정보: {width}x{height}, {fps}fps, {total_frames}프레임")

        # 모듈 초기화
        self.initialize_modules(width, height)

        # 프레임 스킵 (video.frame_skip)
        video_cfg = self.config.get('video', {})
        frame_skip = max(1, int(video_cfg.get('frame_skip', 1)))

        # 출력 비디오 설정 — 브라우저 호환을 위해 H.264(avc1) 우선 시도, 실패 시 mp4v fallback
        out = None
        if output_path:
            effective_fps = max(1, fps // frame_skip)
            out = self._open_video_writer(output_path, effective_fps, width, height)
            if out is None or not out.isOpened():
                logging.error(f"출력 비디오 파일을 열 수 없습니다: {output_path}")
                cap.release()
                return False

        # 처리 시작
        self.is_running = True
        self.start_time = time.time()

        logging.info("비디오 처리 시작...")

        read_idx = 0
        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                # 프레임 스킵: read_idx 가 frame_skip 배수일 때만 처리
                if frame_skip > 1 and (read_idx % frame_skip) != 0:
                    read_idx += 1
                    continue
                read_idx += 1

                # 프레임 처리
                result_frame = self.process_frame(frame)

                # 출력 비디오에 쓰기
                if out:
                    out.write(result_frame)

                # 실시간 표시
                if video_cfg.get('display_realtime', True):
                    cv2.imshow('Vehicle Counting System', result_frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('s'):
                        # 스크린샷 저장
                        screenshot_path = f"screenshot_{int(time.time())}.jpg"
                        cv2.imwrite(screenshot_path, result_frame)
                        logging.info(f"스크린샷 저장: {screenshot_path}")

                # 진행률 표시 및 콜백
                if self.frame_count % 20 == 0 and total_frames > 0:
                    ratio = min(1.0, self.frame_count / total_frames)
                    if self.frame_count % 100 == 0:
                        elapsed_time = time.time() - self.start_time
                        logging.info(
                            f"진행률: {ratio*100:.1f}% "
                            f"({self.frame_count}/{total_frames}), "
                            f"경과시간: {elapsed_time:.1f}초"
                        )
                    if self.progress_callback is not None:
                        try:
                            self.progress_callback(ratio, self.frame_count, total_frames)
                        except Exception as cb_err:
                            logging.debug(f"progress_callback 예외: {cb_err}")
        
        except KeyboardInterrupt:
            logging.info("사용자에 의해 처리 중단됨")
        
        except Exception as e:
            logging.error(f"비디오 처리 중 오류: {e}")
            return False
        
        finally:
            # 정리
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            
            # 최종 결과 출력
            self._print_final_results()
            
            # 결과 저장
            if self.config.get('output', {}).get('save_results', True):
                self._save_results()
        
        return True
    
    def process_webcam(self, camera_index: int = 0) -> bool:
        """웹캠 실시간 처리"""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logging.error(f"웹캠을 열 수 없습니다: {camera_index}")
            return False
        
        # 웹캠 해상도 설정
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 모듈 초기화
        self.initialize_modules(width, height)
        
        # 처리 시작
        self.is_running = True
        self.start_time = time.time()
        
        logging.info("웹캠 실시간 처리 시작... 'q'를 눌러 종료")
        
        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # 프레임 처리
                result_frame = self.process_frame(frame)
                
                # 화면에 표시
                cv2.imshow('Vehicle Counting System - Webcam', result_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    # 카운트 리셋
                    self.counter.reset_counts()
                    logging.info("카운트 리셋됨")
                elif key == ord('s'):
                    # 스크린샷 저장
                    screenshot_path = f"webcam_screenshot_{int(time.time())}.jpg"
                    cv2.imwrite(screenshot_path, result_frame)
                    logging.info(f"스크린샷 저장: {screenshot_path}")
        
        except KeyboardInterrupt:
            logging.info("사용자에 의해 처리 중단됨")
        
        except Exception as e:
            logging.error(f"웹캠 처리 중 오류: {e}")
            return False
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            
            # 최종 결과 출력
            self._print_final_results()
        
        return True
    
    def _print_final_results(self):
        """최종 결과 출력"""
        if not self.counter:
            return
        
        print("\n" + "="*60)
        print("차량 카운팅 시스템 최종 결과")
        print("="*60)
        
        # 기본 통계
        total_time = time.time() - self.start_time if self.start_time else 0
        print(f"처리 시간: {total_time:.1f}초")
        print(f"처리 프레임: {self.frame_count}개")
        
        if self.fps_counter:
            avg_fps = sum(self.fps_counter) / len(self.fps_counter)
            print(f"평균 FPS: {avg_fps:.1f}")
        
        # 카운팅 결과
        print(f"\n{self.counter.get_summary_report()}")
        
        # 성능 통계
        if self.processing_times:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            print(f"\n평균 프레임 처리 시간: {avg_processing_time*1000:.1f}ms")
        
        print("="*60)
    
    def _save_results(self):
        """결과 저장"""
        output_config = self.config.get('output', {})
        
        if not output_config.get('save_results', True):
            return
        
        # JSON 결과 저장 — counter.export_results 는 path traversal 방지를 위해
        # filename 의 디렉터리 성분을 무시한다. 출력 디렉터리는 output_dir 로 분리 전달.
        results_file = output_config.get('results_file', 'counting_results')
        json_path = Path(f"{results_file}.json")
        json_out_dir = json_path.parent
        json_out_dir.mkdir(parents=True, exist_ok=True)
        self.counter.export_results(
            filename=json_path.name, output_dir=str(json_out_dir)
        )
        
        # 차트 생성 및 저장
        try:
            import matplotlib.pyplot as plt
            if self.visualizer:
                # 카운팅 차트
                chart_fig = self.visualizer.create_counting_chart(self.counter)
                if chart_fig:
                    chart_fig.savefig(f"{results_file}_chart.png", dpi=300, bbox_inches='tight')
                    plt.close(chart_fig)

                # 시간별 차트
                hourly_fig = self.visualizer.create_hourly_chart(self.counter)
                if hourly_fig:
                    hourly_fig.savefig(f"{results_file}_hourly.png", dpi=300, bbox_inches='tight')
                    plt.close(hourly_fig)

                logging.info("차트 생성 및 저장 완료")

        except Exception as e:
            logging.warning(f"차트 생성 실패: {e}")

        # 설정 파일 백업 — 실제로 로드된 경로를 사용 (cwd 의존 제거)
        if self.config_path is not None and self.config_path.is_file():
            import shutil
            try:
                shutil.copy2(self.config_path, f"{results_file}_config_backup.yaml")
            except (PermissionError, OSError) as e:
                logging.debug(f"설정 파일 백업 생략: {e}")

        logging.info("결과 저장 완료")
    
    def get_system_status(self) -> Dict:
        """시스템 상태 반환"""
        status = {
            'is_running': self.is_running,
            'frame_count': self.frame_count,
            'processing_time': time.time() - self.start_time if self.start_time else 0,
        }
        
        if self.fps_counter:
            status['current_fps'] = self.fps_counter[-1] if self.fps_counter else 0
            status['avg_fps'] = sum(self.fps_counter) / len(self.fps_counter)
        
        if self.counter:
            status['total_vehicles'] = sum(self.counter.get_total_counts().values())
            status['counting_stats'] = self.counter.get_counting_statistics()
        
        if self.detector:
            status['detection_stats'] = self.detector.get_detection_stats()
        
        if self.tracker:
            status['tracking_stats'] = self.tracker.get_stats()
        
        return status
    
    def stop_processing(self):
        """처리 중단"""
        self.is_running = False
        logging.info("시스템 중단 요청됨")
    
    def update_config(self, new_config: Dict):
        """실시간 설정 업데이트"""
        self.config.update(new_config)
        
        # 모듈별 설정 업데이트
        if self.detector and 'model' in new_config:
            model_config = new_config['model']
            if 'confidence_threshold' in model_config:
                self.detector.update_confidence_threshold(model_config['confidence_threshold'])
        
        if self.counter and 'counting' in new_config:
            counting_config = new_config['counting']
            self.counter.set_counting_parameters(
                min_track_length=counting_config.get('min_track_length'),
                confidence_threshold=counting_config.get('confidence_threshold'),
                count_directions=counting_config.get('directions')
            )
        
        if self.visualizer and 'visualization' in new_config:
            self.visualizer._update_config(new_config['visualization'])
        
        logging.info("설정 업데이트 완료")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='YOLOv8 차선별 차량 카운팅 시스템')
    parser.add_argument('--config', '-c', default='config.yaml', help='설정 파일 경로')
    parser.add_argument('--input', '-i', help='입력 비디오 파일')
    parser.add_argument('--output', '-o', help='출력 비디오 파일')
    parser.add_argument('--webcam', '-w', action='store_true', help='웹캠 사용')
    parser.add_argument('--camera-index', type=int, default=0, help='카메라 인덱스')
    parser.add_argument('--model', '-m', help='YOLO 모델 경로')
    parser.add_argument('--conf', '-t', type=float, help='신뢰도 임계값')
    parser.add_argument('--lanes', '-l', type=int, help='차선 수')
    parser.add_argument('--no-display', action='store_true', help='실시간 화면 표시 안함')
    parser.add_argument('--save-results', '-s', action='store_true', help='결과 저장')
    
    args = parser.parse_args()

    # 인자 검증
    if args.conf is not None and not (0.0 <= args.conf <= 1.0):
        parser.error("--conf 는 0.0 ~ 1.0 범위여야 합니다.")
    if args.lanes is not None and not (1 <= args.lanes <= 20):
        parser.error("--lanes 는 1 ~ 20 범위여야 합니다.")
    if args.camera_index < 0:
        parser.error("--camera-index 는 0 이상이어야 합니다.")
    if args.input and not Path(args.input).is_file():
        parser.error(f"입력 파일을 찾을 수 없습니다: {args.input}")
    if args.model and not Path(args.model).is_file():
        # yolov8*.pt 같은 short-name 은 ultralytics 가 자동 다운로드하므로 경고만
        logging.warning(
            f"지정된 모델 파일이 로컬에 없습니다: {args.model} "
            "(ultralytics 자동 다운로드 시도 예정)"
        )

    # 시스템 초기화
    system = VehicleCountingSystem(args.config)
    
    # 명령행 인자로 설정 오버라이드
    config_override = {}
    
    if args.model:
        config_override['model'] = {'path': args.model}
    
    if args.conf:
        if 'model' not in config_override:
            config_override['model'] = {}
        config_override['model']['confidence_threshold'] = args.conf
    
    if args.lanes:
        config_override['lanes'] = {'mode': 'auto', 'count': args.lanes}
    
    if args.no_display:
        config_override['video'] = {'display_realtime': False}
    
    if args.save_results:
        config_override['output'] = {'save_results': True}
    
    if args.input:
        config_override['video'] = config_override.get('video', {})
        config_override['video']['input_path'] = args.input
    
    if args.output:
        config_override['video'] = config_override.get('video', {})
        config_override['video']['output_path'] = args.output
        config_override['video']['save_output'] = True
    
    # 설정 업데이트
    if config_override:
        system.update_config(config_override)
    
    try:
        # 처리 모드 선택
        if args.webcam:
            success = system.process_webcam(args.camera_index)
        else:
            input_path = args.input or system.config.get('video', {}).get('input_path')
            if not input_path:
                print("입력 비디오 파일을 지정해주세요. --input 옵션을 사용하거나 config.yaml에서 설정하세요.")
                return 1
            
            output_path = args.output or system.config.get('video', {}).get('output_path')
            success = system.process_video(input_path, output_path)
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        logging.info("사용자에 의해 프로그램이 중단되었습니다.")
        return 0
    
    except Exception as e:
        logging.error(f"프로그램 실행 중 오류 발생: {e}")
        return 1


if __name__ == "__main__":
    exit(main())