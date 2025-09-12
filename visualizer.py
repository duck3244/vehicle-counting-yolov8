"""
시각화 모듈
차량 감지, 추적, 카운팅 결과의 시각화
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import logging
from collections import defaultdict


class VehicleVisualizer:
    """차량 카운팅 시각화 클래스"""
    
    def __init__(self, config: Dict = None):
        """
        시각화기 초기화
        
        Args:
            config (Dict): 시각화 설정
        """
        # 기본 설정
        self.config = {
            'colors': {
                'car': (0, 255, 0),          # 초록색
                'truck': (255, 0, 0),        # 빨간색
                'bus': (0, 0, 255),          # 파란색
                'motorcycle': (255, 255, 0), # 노란색
                'lane_line': (255, 255, 255),     # 흰색
                'counting_line': (0, 255, 0),     # 초록색
                'track_history': (255, 0, 255),   # 마젠타
                'text': (255, 255, 255),          # 흰색
                'background': (0, 0, 0)           # 검은색
            },
            'line_thickness': {
                'bbox': 2,
                'lane_line': 2,
                'counting_line': 3,
                'track_history': 2
            },
            'font': {
                'scale': 0.6,
                'thickness': 2
            },
            'display': {
                'show_bbox': True,
                'show_track_id': True,
                'show_confidence': True,
                'show_class': True,
                'show_track_history': True,
                'show_speed': False,
                'history_length': 20
            }
        }
        
        # 사용자 설정으로 업데이트
        if config:
            self._update_config(config)
        
        logging.info("VehicleVisualizer 초기화 완료")
    
    def _update_config(self, config: Dict):
        """설정 업데이트"""
        for key, value in config.items():
            if key in self.config and isinstance(self.config[key], dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def draw_vehicles(self, frame: np.ndarray, vehicles: List[Dict]) -> np.ndarray:
        """
        차량 감지 결과 그리기
        
        Args:
            frame (np.ndarray): 프레임
            vehicles (List[Dict]): 차량 리스트
            
        Returns:
            np.ndarray: 시각화된 프레임
        """
        result_frame = frame.copy()
        
        for vehicle in vehicles:
            if self.config['display']['show_bbox']:
                result_frame = self._draw_vehicle_bbox(result_frame, vehicle)
            
            if self.config['display']['show_track_history']:
                result_frame = self._draw_track_history(result_frame, vehicle)
        
        return result_frame
    
    def _draw_vehicle_bbox(self, frame: np.ndarray, vehicle: Dict) -> np.ndarray:
        """차량 바운딩 박스 그리기"""
        bbox = vehicle.get('bbox')
        if not bbox:
            return frame
        
        x1, y1, x2, y2 = bbox
        class_name = vehicle.get('class_name', 'unknown')
        confidence = vehicle.get('confidence', 0)
        track_id = vehicle.get('track_id')
        
        # 색상 선택
        color = self.config['colors'].get(class_name, (255, 255, 255))
        
        # 바운딩 박스 그리기
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 
                     self.config['line_thickness']['bbox'])
        
        # 라벨 구성
        label_parts = []
        if self.config['display']['show_track_id'] and track_id is not None:
            label_parts.append(f"ID:{track_id}")
        if self.config['display']['show_class']:
            label_parts.append(class_name)
        if self.config['display']['show_confidence']:
            label_parts.append(f"{confidence:.2f}")
        
        label = " ".join(label_parts)
        
        # 라벨 배경과 텍스트
        if label:
            self._draw_label(frame, label, (x1, y1), color)
        
        # 중심점 표시
        center = vehicle.get('center')
        if center:
            cv2.circle(frame, center, 3, color, -1)
        
        return frame
    
    def _draw_track_history(self, frame: np.ndarray, vehicle: Dict) -> np.ndarray:
        """추적 히스토리 그리기"""
        track_history = vehicle.get('track_history', [])
        if len(track_history) < 2:
            return frame
        
        track_id = vehicle.get('track_id', 0)
        
        # 트랙별 고유 색상
        color_idx = track_id % 6 if track_id else 0
        colors = [
            (255, 0, 255),  # 마젠타
            (0, 255, 255),  # 시안
            (255, 255, 0),  # 노란색
            (255, 0, 0),    # 빨간색
            (0, 255, 0),    # 초록색
            (0, 0, 255)     # 파란색
        ]
        track_color = colors[color_idx]
        
        # 히스토리 길이 제한
        max_length = self.config['display']['history_length']
        if len(track_history) > max_length:
            track_history = track_history[-max_length:]
        
        # 경로 그리기
        for i in range(1, len(track_history)):
            cv2.line(frame, track_history[i-1], track_history[i], 
                    track_color, self.config['line_thickness']['track_history'])
        
        # 방향 화살표
        if len(track_history) >= 2:
            self._draw_direction_arrow(frame, track_history[-2], 
                                     track_history[-1], track_color)
        
        return frame
    
    def _draw_direction_arrow(self, frame: np.ndarray, p1: Tuple[int, int], 
                            p2: Tuple[int, int], color: Tuple[int, int, int]):
        """방향 화살표 그리기"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        length = np.sqrt(dx*dx + dy*dy)
        if length < 5:
            return
        
        # 단위 벡터
        ux = dx / length
        uy = dy / length
        
        # 화살표 크기
        arrow_length = min(15, length * 0.3)
        
        # 화살표 끝점들
        arrow_p1 = (
            int(p2[0] - arrow_length * (ux + uy * 0.5)),
            int(p2[1] - arrow_length * (uy - ux * 0.5))
        )
        arrow_p2 = (
            int(p2[0] - arrow_length * (ux - uy * 0.5)),
            int(p2[1] - arrow_length * (uy + ux * 0.5))
        )
        
        cv2.line(frame, p2, arrow_p1, color, 2)
        cv2.line(frame, p2, arrow_p2, color, 2)
    
    def _draw_label(self, frame: np.ndarray, text: str, position: Tuple[int, int], 
                   color: Tuple[int, int, int]):
        """라벨 그리기 (배경 포함)"""
        x, y = position
        font_scale = self.config['font']['scale']
        thickness = self.config['font']['thickness']
        
        # 텍스트 크기 계산
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        
        # 배경 사각형
        cv2.rectangle(frame, (x, y - text_height - 5), 
                     (x + text_width, y + baseline), color, -1)
        
        # 텍스트
        cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, self.config['colors']['text'], thickness)
    
    def draw_lanes(self, frame: np.ndarray, lane_manager) -> np.ndarray:
        """차선 그리기"""
        result_frame = frame.copy()
        height, width = frame.shape[:2]
        
        # 차선 경계선
        for i, (y_start, y_end) in enumerate(lane_manager.lanes):
            if i > 0:  # 첫 번째 차선 제외
                cv2.line(result_frame, (0, y_start), (width, y_start),
                        self.config['colors']['lane_line'], 
                        self.config['line_thickness']['lane_line'])
            
            # 차선 번호
            cv2.putText(result_frame, f'Lane {i+1}', (10, y_start + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, 
                       self.config['colors']['lane_line'], 2)
        
        # 카운팅 라인
        for counting_y in lane_manager.counting_lines:
            cv2.line(result_frame, (0, counting_y), (width, counting_y),
                    self.config['colors']['counting_line'],
                    self.config['line_thickness']['counting_line'])
        
        return result_frame
    
    def draw_statistics_panel(self, frame: np.ndarray, counter, 
                            position: Tuple[int, int] = None) -> np.ndarray:
        """통계 패널 그리기"""
        result_frame = frame.copy()
        height, width = frame.shape[:2]
        
        if position is None:
            x, y = width - 320, 20
        else:
            x, y = position
        
        # 배경 패널
        panel_width = 300
        panel_height = self._calculate_panel_height(counter)
        
        overlay = result_frame.copy()
        cv2.rectangle(overlay, (x, y), (x + panel_width, y + panel_height),
                     self.config['colors']['background'], -1)
        cv2.addWeighted(overlay, 0.8, result_frame, 0.2, 0, result_frame)
        
        # 패널 테두리
        cv2.rectangle(result_frame, (x, y), (x + panel_width, y + panel_height),
                     self.config['colors']['text'], 2)
        
        # 제목
        title_y = y + 25
        cv2.putText(result_frame, "Vehicle Statistics", (x + 10, title_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                   self.config['colors']['text'], 2)
        
        # 통계 정보 그리기
        current_y = self._draw_total_counts(result_frame, counter, x + 10, title_y + 20)
        current_y = self._draw_lane_counts(result_frame, counter, x + 10, current_y + 15)
        current_y = self._draw_rates(result_frame, counter, x + 10, current_y + 15)
        
        return result_frame
    
    def _calculate_panel_height(self, counter) -> int:
        """패널 높이 계산"""
        base_height = 60  # 제목 + 여백
        total_counts_height = len(counter.get_total_counts()) * 20 + 30
        lane_counts_height = len(counter.get_lane_counts()) * 20 + 30
        rates_height = 40
        
        return base_height + total_counts_height + lane_counts_height + rates_height
    
    def _draw_total_counts(self, frame: np.ndarray, counter, x: int, y: int) -> int:
        """전체 카운트 그리기"""
        cv2.putText(frame, "Total Counts:", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   self.config['colors']['text'], 1)
        y += 20
        
        total_counts = counter.get_total_counts()
        for vehicle_type, count in total_counts.items():
            color = self.config['colors'].get(vehicle_type, self.config['colors']['text'])
            cv2.putText(frame, f"  {vehicle_type}: {count}", (x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            y += 18
        
        # 총합
        total = sum(total_counts.values())
        cv2.putText(frame, f"  Total: {total}", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                   self.config['colors']['text'], 2)
        
        return y
    
    def _draw_lane_counts(self, frame: np.ndarray, counter, x: int, y: int) -> int:
        """차선별 카운트 그리기"""
        lane_counts = counter.get_lane_counts()
        if not lane_counts:
            return y
        
        cv2.putText(frame, "Lane Counts:", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   self.config['colors']['text'], 1)
        y += 20
        
        for lane_idx in sorted(lane_counts.keys()):
            lane_total = sum(lane_counts[lane_idx].values())
            cv2.putText(frame, f"  Lane {lane_idx+1}: {lane_total}", (x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                       self.config['colors']['text'], 1)
            y += 18
        
        return y
    
    def _draw_rates(self, frame: np.ndarray, counter, x: int, y: int) -> int:
        """카운팅 비율 그리기"""
        rates = counter.get_counting_rate(60)  # 1분간 비율
        if not rates:
            return y
        
        cv2.putText(frame, "Rate (veh/min):", (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   self.config['colors']['text'], 1)
        y += 20
        
        for vehicle_type, rate in rates.items():
            cv2.putText(frame, f"  {vehicle_type}: {rate:.1f}", (x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                       self.config['colors']['text'], 1)
            y += 18
        
        return y
    
    def create_counting_chart(self, counter, save_path: str = None) -> Optional[plt.Figure]:
        """카운팅 차트 생성"""
        total_counts = counter.get_total_counts()
        if not total_counts:
            return None
        
        # 차트 생성
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # 차량 타입별 원형 차트
        vehicle_types = list(total_counts.keys())
        counts = list(total_counts.values())
        colors = [self._get_matplotlib_color(vtype) for vtype in vehicle_types]
        
        ax1.pie(counts, labels=vehicle_types, colors=colors, autopct='%1.1f%%')
        ax1.set_title('Vehicle Type Distribution')
        
        # 차선별 막대 차트
        lane_counts = counter.get_lane_counts()
        if lane_counts:
            lanes = [f'Lane {i+1}' for i in sorted(lane_counts.keys())]
            lane_totals = [sum(lane_counts[i].values()) for i in sorted(lane_counts.keys())]
            
            ax2.bar(lanes, lane_totals, color='skyblue')
            ax2.set_title('Lane Distribution')
            ax2.set_ylabel('Vehicle Count')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logging.info(f"차트 저장 완료: {save_path}")
        
        return fig
    
    def create_hourly_chart(self, counter, save_path: str = None) -> Optional[plt.Figure]:
        """시간별 카운팅 차트 생성"""
        hourly_counts = counter.get_hourly_counts()
        if not hourly_counts:
            return None
        
        # 시간 순서로 정렬
        hours = sorted(hourly_counts.keys())
        
        # 차량 타입별 데이터 준비
        vehicle_types = set()
        for hour_data in hourly_counts.values():
            vehicle_types.update(hour_data.keys())
        vehicle_types = sorted(list(vehicle_types))
        
        # 데이터 행렬 생성
        data_matrix = []
        for vtype in vehicle_types:
            row = [hourly_counts[hour].get(vtype, 0) for hour in hours]
            data_matrix.append(row)
        
        # 차트 생성
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 스택 바 차트
        bottom = np.zeros(len(hours))
        colors = [self._get_matplotlib_color(vtype) for vtype in vehicle_types]
        
        for i, (vtype, data) in enumerate(zip(vehicle_types, data_matrix)):
            ax.bar(hours, data, bottom=bottom, label=vtype, color=colors[i])
            bottom += data
        
        ax.set_title('Hourly Vehicle Counts')
        ax.set_xlabel('Hour')
        ax.set_ylabel('Vehicle Count')
        ax.legend()
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logging.info(f"시간별 차트 저장 완료: {save_path}")
        
        return fig
    
    def create_heatmap(self, counter, save_path: str = None) -> Optional[plt.Figure]:
        """차선-시간 히트맵 생성"""
        lane_counts = counter.get_lane_counts()
        hourly_counts = counter.get_hourly_counts()
        
        if not lane_counts or not hourly_counts:
            return None
        
        # 데이터 준비
        lanes = sorted(lane_counts.keys())
        hours = sorted(hourly_counts.keys())
        
        # 히트맵 데이터 행렬 (임시로 랜덤 데이터 사용, 실제로는 시간-차선 교차 데이터 필요)
        heatmap_data = np.random.randint(0, 20, size=(len(lanes), len(hours)))
        
        # 히트맵 생성
        fig, ax = plt.subplots(figsize=(12, 6))
        
        sns.heatmap(heatmap_data, 
                   xticklabels=[f"{h}:00" for h in hours],
                   yticklabels=[f"Lane {l+1}" for l in lanes],
                   annot=True, fmt='d', cmap='YlOrRd', ax=ax)
        
        ax.set_title('Lane-Hour Heatmap')
        ax.set_xlabel('Hour')
        ax.set_ylabel('Lane')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logging.info(f"히트맵 저장 완료: {save_path}")
        
        return fig
    
    def _get_matplotlib_color(self, vehicle_type: str) -> str:
        """matplotlib용 색상 변환"""
        color_map = {
            'car': 'green',
            'truck': 'red', 
            'bus': 'blue',
            'motorcycle': 'yellow'
        }
        return color_map.get(vehicle_type, 'gray')
    
    def draw_speed_info(self, frame: np.ndarray, vehicle: Dict, 
                       tracker=None) -> np.ndarray:
        """속도 정보 그리기"""
        if not tracker or not vehicle.get('track_id'):
            return frame
        
        track_id = vehicle['track_id']
        speed = tracker.get_average_speed(track_id)
        
        if speed > 0:
            center = vehicle.get('center')
            if center:
                speed_text = f"{speed:.1f} km/h"
                self._draw_label(frame, speed_text, 
                               (center[0] - 30, center[1] + 20),
                               self.config['colors']['text'])
        
        return frame
    
    def draw_counting_zones(self, frame: np.ndarray, lane_manager) -> np.ndarray:
        """카운팅 존 시각화"""
        result_frame = frame.copy()
        
        for i, counting_line in enumerate(lane_manager.counting_lines):
            # 카운팅 존 (라인 위아래 일정 범위)
            zone_height = 20
            y1 = counting_line - zone_height
            y2 = counting_line + zone_height
            
            # 반투명 오버레이
            overlay = result_frame.copy()
            cv2.rectangle(overlay, (0, y1), (frame.shape[1], y2),
                         self.config['colors']['counting_line'], -1)
            cv2.addWeighted(overlay, 0.3, result_frame, 0.7, 0, result_frame)
            
            # 존 라벨
            cv2.putText(result_frame, f"Count Zone {i+1}", (10, counting_line),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                       self.config['colors']['counting_line'], 2)
        
        return result_frame
    
    def create_dashboard_frame(self, frame: np.ndarray, vehicles: List[Dict],
                              lane_manager, counter, tracker=None) -> np.ndarray:
        """통합 대시보드 프레임 생성"""
        result_frame = frame.copy()
        
        # 1. 차선 그리기
        result_frame = self.draw_lanes(result_frame, lane_manager)
        
        # 2. 차량 그리기
        result_frame = self.draw_vehicles(result_frame, vehicles)
        
        # 3. 속도 정보 (옵션)
        if self.config['display']['show_speed'] and tracker:
            for vehicle in vehicles:
                result_frame = self.draw_speed_info(result_frame, vehicle, tracker)
        
        # 4. 통계 패널
        result_frame = self.draw_statistics_panel(result_frame, counter)
        
        # 5. 프레임 정보
        result_frame = self._draw_frame_info(result_frame)
        
        return result_frame
    
    def _draw_frame_info(self, frame: np.ndarray) -> np.ndarray:
        """프레임 정보 그리기"""
        import time
        
        # 현재 시간
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, current_time, (10, frame.shape[0] - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                   self.config['colors']['text'], 1)
        
        # FPS 정보 (간단한 예시)
        cv2.putText(frame, "FPS: 30", (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                   self.config['colors']['text'], 1)
        
        return frame
    
    def save_visualization_config(self, filename: str = "viz_config.json"):
        """시각화 설정 저장"""
        import json
        
        with open(filename, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        logging.info(f"시각화 설정 저장 완료: {filename}")
    
    def load_visualization_config(self, filename: str) -> bool:
        """시각화 설정 로드"""
        import json
        
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            
            self._update_config(config)
            logging.info(f"시각화 설정 로드 완료: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"시각화 설정 로드 실패: {e}")
            return False
    
    def create_summary_video_frame(self, counter, frame_size: Tuple[int, int]) -> np.ndarray:
        """요약 비디오 프레임 생성"""
        width, height = frame_size
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 제목
        title = "Vehicle Counting Summary"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        title_x = (width - title_size[0]) // 2
        cv2.putText(frame, title, (title_x, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        # 통계 정보
        total_counts = counter.get_total_counts()
        y = 150
        
        for vehicle_type, count in total_counts.items():
            text = f"{vehicle_type}: {count}"
            cv2.putText(frame, text, (50, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            y += 50
        
        # 총계
        total = sum(total_counts.values())
        cv2.putText(frame, f"Total: {total}", (50, y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        
        return frame
    
    def create_comparison_frame(self, frames: List[np.ndarray], 
                              labels: List[str]) -> np.ndarray:
        """비교 프레임 생성 (여러 프레임을 하나로 합성)"""
        if not frames or len(frames) != len(labels):
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 프레임 크기 통일
        target_height = 240
        target_width = 320
        
        resized_frames = []
        for frame in frames:
            resized = cv2.resize(frame, (target_width, target_height))
            resized_frames.append(resized)
        
        # 2x2 그리드로 배치 (최대 4개)
        if len(resized_frames) <= 2:
            result = np.hstack(resized_frames)
        else:
            top_row = np.hstack(resized_frames[:2])
            bottom_row = np.hstack(resized_frames[2:4])
            result = np.vstack([top_row, bottom_row])
        
        # 라벨 추가
        for i, label in enumerate(labels[:len(resized_frames)]):
            if i < 2:
                x = i * target_width + 10
                y = 30
            else:
                x = (i-2) * target_width + 10
                y = target_height + 30
            
            cv2.putText(result, label, (x, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return result
    
    def update_display_settings(self, **kwargs):
        """디스플레이 설정 업데이트"""
        for key, value in kwargs.items():
            if key in self.config['display']:
                self.config['display'][key] = value
                logging.info(f"디스플레이 설정 업데이트: {key} = {value}")


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 시각화기 생성
    visualizer = VehicleVisualizer()
    
    # 테스트 프레임
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 테스트 차량 데이터
    test_vehicles = [
        {
            'bbox': (100, 100, 200, 200),
            'class_name': 'car',
            'confidence': 0.9,
            'track_id': 1,
            'center': (150, 150),
            'track_history': [(140, 140), (145, 145), (150, 150)]
        }
    ]
    
    # 시각화 테스트
    result_frame = visualizer.draw_vehicles(test_frame, test_vehicles)
    print("시각화 테스트 완료")
    
    # 설정 저장 테스트
    visualizer.save_visualization_config("test_viz_config.json")
    print("설정 저장 완료")