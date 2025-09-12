"""
차량 추적 모듈
차량의 이동 경로 추적 및 관리
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
import logging
import time


class VehicleTracker:
    """차량 추적 관리 클래스"""
    
    def __init__(self, max_history_length: int = 50, max_disappeared: int = 30):
        """
        차량 추적기 초기화
        
        Args:
            max_history_length (int): 최대 추적 히스토리 길이
            max_disappeared (int): 최대 사라진 프레임 수
        """
        self.max_history_length = max_history_length
        self.max_disappeared = max_disappeared
        
        # 추적 데이터
        self.tracks = {}  # track_id: TrackInfo
        self.track_history = defaultdict(lambda: deque(maxlen=max_history_length))
        self.disappeared_counts = defaultdict(int)
        
        # 통계
        self.stats = {
            'total_tracks': 0,
            'active_tracks': 0,
            'lost_tracks': 0,
            'avg_track_length': 0
        }
        
        logging.info("VehicleTracker 초기화 완료")
    
    def update_tracks(self, vehicles: List[Dict]) -> List[Dict]:
        """
        차량 추적 정보 업데이트
        
        Args:
            vehicles (List[Dict]): 감지된 차량 리스트
            
        Returns:
            List[Dict]: 추적 정보가 추가된 차량 리스트
        """
        updated_vehicles = []
        current_track_ids = set()
        
        for vehicle in vehicles:
            track_id = vehicle.get('track_id')
            
            if track_id is not None:
                current_track_ids.add(track_id)
                
                # 새로운 트랙인지 확인
                if track_id not in self.tracks:
                    self._create_new_track(track_id, vehicle)
                
                # 트랙 정보 업데이트
                self._update_track(track_id, vehicle)
                
                # 사라진 카운트 리셋
                self.disappeared_counts[track_id] = 0
                
                # 추적 정보 추가
                vehicle['track_info'] = self.tracks[track_id]
                updated_vehicles.append(vehicle)
        
        # 사라진 트랙 처리
        self._handle_disappeared_tracks(current_track_ids)
        
        # 통계 업데이트
        self._update_stats()
        
        return updated_vehicles
    
    def _create_new_track(self, track_id: int, vehicle: Dict):
        """새로운 트랙 생성"""
        self.tracks[track_id] = {
            'id': track_id,
            'class_name': vehicle['class_name'],
            'first_seen': time.time(),
            'last_seen': time.time(),
            'total_detections': 1,
            'avg_confidence': vehicle['confidence'],
            'path_length': 0,
            'speed_history': deque(maxlen=10),
            'size_history': deque(maxlen=10),
            'is_active': True
        }
        
        # 히스토리 시작
        center = vehicle['center']
        self.track_history[track_id].append(center)
        
        self.stats['total_tracks'] += 1
        logging.debug(f"새로운 트랙 생성: {track_id}")
    
    def _update_track(self, track_id: int, vehicle: Dict):
        """기존 트랙 정보 업데이트"""
        track_info = self.tracks[track_id]
        center = vehicle['center']
        
        # 기본 정보 업데이트
        track_info['last_seen'] = time.time()
        track_info['total_detections'] += 1
        
        # 평균 신뢰도 업데이트
        total_conf = (track_info['avg_confidence'] * (track_info['total_detections'] - 1) + 
                     vehicle['confidence'])
        track_info['avg_confidence'] = total_conf / track_info['total_detections']
        
        # 경로 길이 계산
        if len(self.track_history[track_id]) > 0:
            prev_center = self.track_history[track_id][-1]
            distance = np.sqrt((center[0] - prev_center[0])**2 + 
                             (center[1] - prev_center[1])**2)
            track_info['path_length'] += distance
        
        # 히스토리 추가
        self.track_history[track_id].append(center)
        
        # 크기 히스토리 추가
        track_info['size_history'].append(vehicle['area'])
    
    def _handle_disappeared_tracks(self, current_track_ids: set):
        """사라진 트랙 처리"""
        all_track_ids = set(self.tracks.keys())
        disappeared_track_ids = all_track_ids - current_track_ids
        
        for track_id in disappeared_track_ids:
            if not self.tracks[track_id]['is_active']:
                continue
                
            self.disappeared_counts[track_id] += 1
            
            # 너무 오래 사라진 트랙 비활성화
            if self.disappeared_counts[track_id] >= self.max_disappeared:
                self.tracks[track_id]['is_active'] = False
                self.stats['lost_tracks'] += 1
                logging.debug(f"트랙 비활성화: {track_id}")
    
    def _update_stats(self):
        """통계 업데이트"""
        active_tracks = sum(1 for track in self.tracks.values() if track['is_active'])
        self.stats['active_tracks'] = active_tracks
        
        if self.stats['total_tracks'] > 0:
            total_length = sum(track['path_length'] for track in self.tracks.values())
            self.stats['avg_track_length'] = total_length / self.stats['total_tracks']
    
    def get_track_history(self, track_id: int, max_points: int = None) -> List[Tuple[int, int]]:
        """
        특정 트랙의 히스토리 반환
        
        Args:
            track_id (int): 트랙 ID
            max_points (int): 최대 포인트 수
            
        Returns:
            List[Tuple]: 좌표 리스트
        """
        history = list(self.track_history[track_id])
        if max_points and len(history) > max_points:
            return history[-max_points:]
        return history
    
    def calculate_speed(self, track_id: int, fps: float = 30, 
                       pixel_per_meter: float = 10) -> float:
        """
        차량 속도 계산
        
        Args:
            track_id (int): 트랙 ID
            fps (float): 비디오 FPS
            pixel_per_meter (float): 미터당 픽셀 수
            
        Returns:
            float: 속도 (km/h)
        """
        history = self.track_history[track_id]
        
        if len(history) < 5:  # 최소 5개 포인트 필요
            return 0.0
        
        # 최근 몇 프레임의 이동 거리 계산
        recent_points = list(history)[-5:]
        total_distance = 0
        
        for i in range(1, len(recent_points)):
            x1, y1 = recent_points[i-1]
            x2, y2 = recent_points[i]
            distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_distance += distance
        
        # 픽셀 거리를 미터로 변환
        distance_meters = total_distance / pixel_per_meter
        
        # 시간 계산 (프레임 수 / FPS)
        time_seconds = (len(recent_points) - 1) / fps
        
        if time_seconds <= 0:
            return 0.0
        
        # 속도 계산 (m/s to km/h)
        speed_ms = distance_meters / time_seconds
        speed_kmh = speed_ms * 3.6
        
        # 속도 히스토리에 추가
        if track_id in self.tracks:
            self.tracks[track_id]['speed_history'].append(speed_kmh)
        
        return speed_kmh
    
    def get_average_speed(self, track_id: int) -> float:
        """평균 속도 반환"""
        if track_id not in self.tracks:
            return 0.0
        
        speed_history = self.tracks[track_id]['speed_history']
        if len(speed_history) == 0:
            return 0.0
        
        return sum(speed_history) / len(speed_history)
    
    def draw_tracks(self, frame: np.ndarray, vehicles: List[Dict], 
                   show_history: bool = True, show_speed: bool = False,
                   history_length: int = 20) -> np.ndarray:
        """
        추적 정보를 프레임에 그리기
        
        Args:
            frame (np.ndarray): 프레임
            vehicles (List[Dict]): 차량 리스트
            show_history (bool): 히스토리 표시 여부
            show_speed (bool): 속도 표시 여부
            history_length (int): 표시할 히스토리 길이
            
        Returns:
            np.ndarray: 그려진 프레임
        """
        result_frame = frame.copy()
        
        for vehicle in vehicles:
            track_id = vehicle.get('track_id')
            if track_id is None:
                continue
            
            # 추적 경로 그리기
            if show_history:
                history = self.get_track_history(track_id, history_length)
                if len(history) > 1:
                    # 경로 색상 (트랙 ID에 따라 다른 색상)
                    color_idx = track_id % 6
                    colors = [(255, 0, 255), (0, 255, 255), (255, 255, 0),
                             (255, 0, 0), (0, 255, 0), (0, 0, 255)]
                    track_color = colors[color_idx]
                    
                    # 선 그리기
                    for i in range(1, len(history)):
                        cv2.line(result_frame, history[i-1], history[i], track_color, 2)
                    
                    # 방향 화살표
                    if len(history) >= 2:
                        p1 = history[-2]
                        p2 = history[-1]
                        self._draw_arrow(result_frame, p1, p2, track_color)
            
            # 속도 정보 표시
            if show_speed and track_id in self.tracks:
                speed = self.get_average_speed(track_id)
                if speed > 0:
                    center = vehicle['center']
                    speed_text = f"{speed:.1f} km/h"
                    cv2.putText(result_frame, speed_text, 
                               (center[0] - 30, center[1] + 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return result_frame
    
    def _draw_arrow(self, frame: np.ndarray, p1: Tuple[int, int], 
                   p2: Tuple[int, int], color: Tuple[int, int, int]):
        """화살표 그리기"""
        # 벡터 계산
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # 벡터 길이
        length = np.sqrt(dx*dx + dy*dy)
        if length < 5:  # 너무 짧으면 그리지 않음
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
        
        # 화살표 그리기
        cv2.line(frame, p2, arrow_p1, color, 2)
        cv2.line(frame, p2, arrow_p2, color, 2)
    
    def get_track_info(self, track_id: int) -> Optional[Dict]:
        """트랙 정보 반환"""
        return self.tracks.get(track_id)
    
    def get_active_tracks(self) -> List[int]:
        """활성 트랙 ID 리스트 반환"""
        return [track_id for track_id, track_info in self.tracks.items() 
                if track_info['is_active']]
    
    def get_stats(self) -> Dict:
        """추적 통계 반환"""
        return self.stats.copy()
    
    def cleanup_old_tracks(self, max_age_seconds: float = 300):
        """오래된 트랙 정리"""
        current_time = time.time()
        tracks_to_remove = []
        
        for track_id, track_info in self.tracks.items():
            if not track_info['is_active']:
                age = current_time - track_info['last_seen']
                if age > max_age_seconds:
                    tracks_to_remove.append(track_id)
        
        # 트랙 제거
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
            if track_id in self.track_history:
                del self.track_history[track_id]
            if track_id in self.disappeared_counts:
                del self.disappeared_counts[track_id]
        
        if tracks_to_remove:
            logging.info(f"오래된 트랙 {len(tracks_to_remove)}개 정리")
    
    def export_track_data(self, track_id: int) -> Dict:
        """특정 트랙의 모든 데이터 내보내기"""
        if track_id not in self.tracks:
            return {}
        
        track_info = self.tracks[track_id].copy()
        track_info['history'] = list(self.track_history[track_id])
        track_info['speed_history'] = list(track_info['speed_history'])
        track_info['size_history'] = list(track_info['size_history'])
        
        return track_info
    
    def reset(self):
        """추적기 초기화"""
        self.tracks.clear()
        self.track_history.clear()
        self.disappeared_counts.clear()
        
        self.stats = {
            'total_tracks': 0,
            'active_tracks': 0,
            'lost_tracks': 0,
            'avg_track_length': 0
        }
        
        logging.info("VehicleTracker 초기화 완료")


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    tracker = VehicleTracker()
    
    # 테스트 차량 데이터
    test_vehicles = [
        {
            'track_id': 1,
            'class_name': 'car',
            'center': (100, 200),
            'confidence': 0.9,
            'area': 5000
        },
        {
            'track_id': 2,
            'class_name': 'truck',
            'center': (200, 300),
            'confidence': 0.8,
            'area': 8000
        }
    ]
    
    # 추적 업데이트 테스트
    updated_vehicles = tracker.update_tracks(test_vehicles)
    print(f"업데이트된 차량 수: {len(updated_vehicles)}")
    print(f"추적 통계: {tracker.get_stats()}")
    
    # 속도 계산 테스트
    for vehicle in updated_vehicles:
        track_id = vehicle['track_id']
        speed = tracker.calculate_speed(track_id)
        print(f"트랙 {track_id} 속도: {speed:.2f} km/h")