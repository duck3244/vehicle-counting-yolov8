"""
카운팅 모듈
차량 카운팅 로직 및 통계 관리
"""

import cv2
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Set
import time
import json
import logging


class VehicleCounter:
    """차량 카운팅 관리 클래스"""
    
    def __init__(self, count_directions: List[str] = None):
        """
        카운터 초기화
        
        Args:
            count_directions (List[str]): 카운팅할 방향 ['up', 'down', 'both']
        """
        if count_directions is None:
            count_directions = ['both']
        
        self.count_directions = count_directions
        
        # 카운팅 데이터
        self.total_counts = defaultdict(int)  # {vehicle_type: count}
        self.lane_counts = defaultdict(lambda: defaultdict(int))  # {lane_idx: {vehicle_type: count}}
        self.direction_counts = defaultdict(lambda: defaultdict(int))  # {direction: {vehicle_type: count}}
        
        # 중복 카운팅 방지
        self.crossed_vehicles = set()  # {(track_id, lane_idx, direction)}
        
        # 시간별 통계
        self.hourly_counts = defaultdict(lambda: defaultdict(int))
        self.counting_session_start = time.time()
        
        # 카운팅 이벤트 로그
        self.counting_events = []  # [{timestamp, track_id, vehicle_type, lane, direction}]
        
        # 설정
        self.min_track_length = 5  # 최소 추적 길이
        self.confidence_threshold = 0.5  # 최소 신뢰도
        
        logging.info("VehicleCounter 초기화 완료")
    
    def process_vehicle_crossing(self, vehicle: Dict, lane_idx: int, 
                               direction: str, track_history: List) -> bool:
        """
        차량 카운팅 라인 통과 처리
        
        Args:
            vehicle (Dict): 차량 정보
            lane_idx (int): 차선 인덱스
            direction (str): 통과 방향 ('up', 'down')
            track_history (List): 추적 히스토리
            
        Returns:
            bool: 카운팅 여부
        """
        track_id = vehicle.get('track_id')
        vehicle_type = vehicle.get('class_name')
        confidence = vehicle.get('confidence', 0)
        
        # 기본 검증
        if not self._validate_counting_conditions(track_id, vehicle_type, 
                                                confidence, track_history, direction):
            return False
        
        # 중복 카운팅 방지
        crossing_key = (track_id, lane_idx, direction)
        if crossing_key in self.crossed_vehicles:
            return False
        
        # 카운팅 실행
        self._execute_counting(vehicle_type, lane_idx, direction, track_id)
        
        # 중복 방지 기록
        self.crossed_vehicles.add(crossing_key)
        
        # 이벤트 로깅
        self._log_counting_event(track_id, vehicle_type, lane_idx, direction, confidence)
        
        logging.debug(f"차량 카운팅: ID={track_id}, Type={vehicle_type}, "
                     f"Lane={lane_idx}, Direction={direction}")
        
        return True
    
    def _validate_counting_conditions(self, track_id: Optional[int], vehicle_type: str,
                                    confidence: float, track_history: List, 
                                    direction: str) -> bool:
        """카운팅 조건 검증"""
        # 추적 ID 확인
        if track_id is None:
            logging.debug("추적 ID가 없어 카운팅 제외")
            return False
        
        # 신뢰도 확인
        if confidence < self.confidence_threshold:
            logging.debug(f"신뢰도 부족으로 카운팅 제외: {confidence}")
            return False
        
        # 추적 길이 확인
        if len(track_history) < self.min_track_length:
            logging.debug(f"추적 길이 부족으로 카운팅 제외: {len(track_history)}")
            return False
        
        # 방향 확인
        if 'both' not in self.count_directions and direction not in self.count_directions:
            logging.debug(f"카운팅 방향 제외: {direction}")
            return False
        
        return True
    
    def _execute_counting(self, vehicle_type: str, lane_idx: int, direction: str, track_id: int):
        """실제 카운팅 실행"""
        # 전체 카운트
        self.total_counts[vehicle_type] += 1
        
        # 차선별 카운트
        self.lane_counts[lane_idx][vehicle_type] += 1
        
        # 방향별 카운트
        self.direction_counts[direction][vehicle_type] += 1
        
        # 시간별 카운트
        current_hour = time.strftime("%H", time.localtime())
        self.hourly_counts[current_hour][vehicle_type] += 1
    
    def _log_counting_event(self, track_id: int, vehicle_type: str, 
                           lane_idx: int, direction: str, confidence: float):
        """카운팅 이벤트 로깅"""
        event = {
            'timestamp': time.time(),
            'datetime': time.strftime("%Y-%m-%d %H:%M:%S"),
            'track_id': track_id,
            'vehicle_type': vehicle_type,
            'lane_index': lane_idx,
            'direction': direction,
            'confidence': confidence
        }
        
        self.counting_events.append(event)
        
        # 이벤트 로그 크기 제한 (최대 10000개)
        if len(self.counting_events) > 10000:
            self.counting_events = self.counting_events[-5000:]
    
    def get_total_counts(self) -> Dict[str, int]:
        """전체 카운트 반환"""
        return dict(self.total_counts)
    
    def get_lane_counts(self) -> Dict[int, Dict[str, int]]:
        """차선별 카운트 반환"""
        return {lane: dict(counts) for lane, counts in self.lane_counts.items()}
    
    def get_direction_counts(self) -> Dict[str, Dict[str, int]]:
        """방향별 카운트 반환"""
        return {direction: dict(counts) for direction, counts in self.direction_counts.items()}
    
    def get_hourly_counts(self) -> Dict[str, Dict[str, int]]:
        """시간별 카운트 반환"""
        return {hour: dict(counts) for hour, counts in self.hourly_counts.items()}
    
    def get_counting_rate(self, time_window: int = 60) -> Dict[str, float]:
        """
        최근 시간 윈도우 내 카운팅 비율 계산
        
        Args:
            time_window (int): 시간 윈도우 (초)
            
        Returns:
            Dict[str, float]: 차량 타입별 분당 카운트
        """
        current_time = time.time()
        recent_events = [
            event for event in self.counting_events
            if current_time - event['timestamp'] <= time_window
        ]
        
        if not recent_events:
            return {}
        
        # 차량 타입별 카운트
        type_counts = Counter(event['vehicle_type'] for event in recent_events)
        
        # 분당 비율로 변환
        minutes = time_window / 60
        return {vehicle_type: count / minutes for vehicle_type, count in type_counts.items()}
    
    def get_peak_hours(self) -> List[Tuple[str, int]]:
        """피크 시간대 반환"""
        hourly_totals = {}
        
        for hour, counts in self.hourly_counts.items():
            hourly_totals[hour] = sum(counts.values())
        
        # 내림차순 정렬
        sorted_hours = sorted(hourly_totals.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_hours[:3]  # 상위 3개 시간대
    
    def get_lane_distribution(self) -> Dict[int, float]:
        """차선별 트래픽 분포 (백분율)"""
        lane_totals = {}
        total_vehicles = 0
        
        for lane_idx, counts in self.lane_counts.items():
            lane_total = sum(counts.values())
            lane_totals[lane_idx] = lane_total
            total_vehicles += lane_total
        
        if total_vehicles == 0:
            return {}
        
        return {lane: (count / total_vehicles) * 100 
                for lane, count in lane_totals.items()}
    
    def get_vehicle_type_distribution(self) -> Dict[str, float]:
        """차량 타입별 분포 (백분율)"""
        total_vehicles = sum(self.total_counts.values())
        
        if total_vehicles == 0:
            return {}
        
        return {vehicle_type: (count / total_vehicles) * 100 
                for vehicle_type, count in self.total_counts.items()}
    
    def draw_counting_info(self, frame: np.ndarray, 
                          position: Tuple[int, int] = None) -> np.ndarray:
        """
        카운팅 정보를 프레임에 그리기
        
        Args:
            frame (np.ndarray): 프레임
            position (Tuple[int, int]): 표시 위치 (기본: 우측 상단)
            
        Returns:
            np.ndarray: 정보가 그려진 프레임
        """
        result_frame = frame.copy()
        height, width = frame.shape[:2]
        
        # 기본 위치 설정
        if position is None:
            x, y = width - 300, 50
        else:
            x, y = position
        
        # 배경 반투명 박스
        overlay = result_frame.copy()
        box_height = len(self.total_counts) * 25 + 100
        cv2.rectangle(overlay, (x-10, y-30), (x+280, y+box_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, result_frame, 0.3, 0, result_frame)
        
        # 제목
        cv2.putText(result_frame, "Vehicle Counts", (x, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 30
        
        # 전체 카운트
        for vehicle_type, count in self.total_counts.items():
            text = f"{vehicle_type}: {count}"
            cv2.putText(result_frame, text, (x, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y += 25
        
        # 총 차량 수
        total_vehicles = sum(self.total_counts.values())
        cv2.putText(result_frame, f"Total: {total_vehicles}", (x, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return result_frame
    
    def draw_lane_counts(self, frame: np.ndarray, lane_positions: List[int]) -> np.ndarray:
        """
        각 차선에 카운트 정보 표시
        
        Args:
            frame (np.ndarray): 프레임
            lane_positions (List[int]): 각 차선의 Y 위치
            
        Returns:
            np.ndarray: 정보가 그려진 프레임
        """
        result_frame = frame.copy()
        
        for lane_idx, y_pos in enumerate(lane_positions):
            if lane_idx not in self.lane_counts:
                continue
            
            lane_total = sum(self.lane_counts[lane_idx].values())
            text = f"Lane {lane_idx+1}: {lane_total}"
            
            # 배경 박스
            (text_width, text_height), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(result_frame, (10, y_pos-20), 
                         (10+text_width+10, y_pos+5), (0, 0, 0), -1)
            
            # 텍스트
            cv2.putText(result_frame, text, (15, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return result_frame
    
    def export_results(self, filename: str = "counting_results.json"):
        """결과를 JSON 파일로 내보내기"""
        results = {
            'session_info': {
                'start_time': self.counting_session_start,
                'duration_seconds': time.time() - self.counting_session_start,
                'count_directions': self.count_directions
            },
            'total_counts': self.get_total_counts(),
            'lane_counts': self.get_lane_counts(),
            'direction_counts': self.get_direction_counts(),
            'hourly_counts': self.get_hourly_counts(),
            'statistics': {
                'peak_hours': self.get_peak_hours(),
                'lane_distribution': self.get_lane_distribution(),
                'vehicle_type_distribution': self.get_vehicle_type_distribution(),
                'counting_rate': self.get_counting_rate()
            },
            'recent_events': self.counting_events[-100:]  # 최근 100개 이벤트
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logging.info(f"카운팅 결과 내보내기 완료: {filename}")
    
    def import_results(self, filename: str) -> bool:
        """결과를 JSON 파일에서 가져오기"""
        try:
            with open(filename, 'r') as f:
                results = json.load(f)
            
            # 카운트 데이터 복원
            if 'total_counts' in results:
                self.total_counts = defaultdict(int, results['total_counts'])
            
            if 'lane_counts' in results:
                self.lane_counts = defaultdict(lambda: defaultdict(int))
                for lane_str, counts in results['lane_counts'].items():
                    lane_idx = int(lane_str)
                    self.lane_counts[lane_idx] = defaultdict(int, counts)
            
            if 'direction_counts' in results:
                self.direction_counts = defaultdict(lambda: defaultdict(int))
                for direction, counts in results['direction_counts'].items():
                    self.direction_counts[direction] = defaultdict(int, counts)
            
            if 'hourly_counts' in results:
                self.hourly_counts = defaultdict(lambda: defaultdict(int))
                for hour, counts in results['hourly_counts'].items():
                    self.hourly_counts[hour] = defaultdict(int, counts)
            
            # 이벤트 로그 복원
            if 'recent_events' in results:
                self.counting_events = results['recent_events']
            
            logging.info(f"카운팅 결과 가져오기 완료: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"카운팅 결과 가져오기 실패: {e}")
            return False
    
    def get_summary_report(self) -> str:
        """요약 리포트 생성"""
        total_vehicles = sum(self.total_counts.values())
        session_duration = time.time() - self.counting_session_start
        
        report = []
        report.append("=== Vehicle Counting Summary ===")
        report.append(f"Session Duration: {session_duration/3600:.1f} hours")
        report.append(f"Total Vehicles: {total_vehicles}")
        report.append("")
        
        # 차량 타입별 카운트
        report.append("Vehicle Types:")
        for vehicle_type, count in sorted(self.total_counts.items()):
            percentage = (count / total_vehicles * 100) if total_vehicles > 0 else 0
            report.append(f"  {vehicle_type}: {count} ({percentage:.1f}%)")
        report.append("")
        
        # 차선별 카운트
        if self.lane_counts:
            report.append("Lane Distribution:")
            for lane_idx in sorted(self.lane_counts.keys()):
                lane_total = sum(self.lane_counts[lane_idx].values())
                percentage = (lane_total / total_vehicles * 100) if total_vehicles > 0 else 0
                report.append(f"  Lane {lane_idx+1}: {lane_total} ({percentage:.1f}%)")
            report.append("")
        
        # 피크 시간대
        peak_hours = self.get_peak_hours()
        if peak_hours:
            report.append("Peak Hours:")
            for hour, count in peak_hours:
                report.append(f"  {hour}:00 - {count} vehicles")
            report.append("")
        
        # 현재 카운팅 비율
        current_rate = self.get_counting_rate(300)  # 최근 5분
        if current_rate:
            report.append("Current Rate (vehicles/min):")
            for vehicle_type, rate in current_rate.items():
                report.append(f"  {vehicle_type}: {rate:.1f}")
        
        return "\n".join(report)
    
    def reset_counts(self):
        """모든 카운트 초기화"""
        self.total_counts.clear()
        self.lane_counts.clear()
        self.direction_counts.clear()
        self.hourly_counts.clear()
        self.crossed_vehicles.clear()
        self.counting_events.clear()
        self.counting_session_start = time.time()
        
        logging.info("카운팅 데이터 초기화 완료")
    
    def set_counting_parameters(self, min_track_length: int = None, 
                              confidence_threshold: float = None,
                              count_directions: List[str] = None):
        """카운팅 파라미터 설정"""
        if min_track_length is not None:
            self.min_track_length = min_track_length
            logging.info(f"최소 추적 길이 설정: {min_track_length}")
        
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
            logging.info(f"신뢰도 임계값 설정: {confidence_threshold}")
        
        if count_directions is not None:
            self.count_directions = count_directions
            logging.info(f"카운팅 방향 설정: {count_directions}")
    
    def get_counting_statistics(self) -> Dict:
        """상세 통계 정보 반환"""
        total_vehicles = sum(self.total_counts.values())
        session_duration = time.time() - self.counting_session_start
        
        stats = {
            'session': {
                'start_time': self.counting_session_start,
                'duration_hours': session_duration / 3600,
                'total_vehicles': total_vehicles,
                'vehicles_per_hour': total_vehicles / (session_duration / 3600) if session_duration > 0 else 0
            },
            'counts': {
                'total': self.get_total_counts(),
                'by_lane': self.get_lane_counts(),
                'by_direction': self.get_direction_counts(),
                'by_hour': self.get_hourly_counts()
            },
            'distributions': {
                'vehicle_types': self.get_vehicle_type_distribution(),
                'lanes': self.get_lane_distribution()
            },
            'rates': {
                'current_5min': self.get_counting_rate(300),
                'current_1min': self.get_counting_rate(60)
            },
            'peak_analysis': {
                'peak_hours': self.get_peak_hours()
            },
            'events': {
                'total_events': len(self.counting_events),
                'recent_events_count': len([e for e in self.counting_events 
                                           if time.time() - e['timestamp'] <= 300])
            }
        }
        
        return stats


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 카운터 생성
    counter = VehicleCounter(['both'])
    
    # 테스트 차량 데이터
    test_vehicle = {
        'track_id': 1,
        'class_name': 'car',
        'confidence': 0.8,
        'center': (100, 200)
    }
    
    # 카운팅 테스트
    success = counter.process_vehicle_crossing(
        test_vehicle, lane_idx=0, direction='down', track_history=[(100, 190), (100, 200)]
    )
    
    print(f"카운팅 성공: {success}")
    print(f"전체 카운트: {counter.get_total_counts()}")
    print(f"차선별 카운트: {counter.get_lane_counts()}")
    
    # 요약 리포트
    print("\n" + counter.get_summary_report())