"""
차선 관리 모듈
차선 설정, 검증, 시각화 기능
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import json
import logging


class LaneManager:
    """차선 관리 클래스"""
    
    def __init__(self, frame_width: int = 1920, frame_height: int = 1080):
        """
        차선 관리자 초기화
        
        Args:
            frame_width (int): 프레임 너비
            frame_height (int): 프레임 높이
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # 차선 설정
        self.lanes = []  # [(y_start, y_end), ...]
        self.counting_lines = []  # [y_position, ...]
        self.lane_names = []  # ['Lane 1', 'Lane 2', ...]
        
        # 시각화 설정
        self.colors = {
            'lane_line': (255, 255, 255),      # 흰색
            'counting_line': (0, 255, 0),      # 초록색
            'lane_number': (255, 255, 0),      # 노란색
            'roi_boundary': (0, 255, 255)      # 시안색
        }
        
        self.line_thickness = {
            'lane_line': 2,
            'counting_line': 3,
            'lane_number': 2
        }
        
        logging.info(f"LaneManager 초기화: {frame_width}x{frame_height}")
    
    def setup_auto_lanes(self, num_lanes: int, margin_top: int = 50, 
                        margin_bottom: int = 50) -> bool:
        """
        자동 차선 설정
        
        Args:
            num_lanes (int): 차선 수
            margin_top (int): 상단 여백
            margin_bottom (int): 하단 여백
            
        Returns:
            bool: 설정 성공 여부
        """
        if num_lanes <= 0:
            logging.error("차선 수는 1 이상이어야 합니다")
            return False
        
        available_height = self.frame_height - margin_top - margin_bottom
        if available_height <= 0:
            logging.error("여백이 너무 커서 차선을 설정할 수 없습니다")
            return False
        
        lane_height = available_height // num_lanes
        
        self.lanes = []
        self.counting_lines = []
        self.lane_names = []
        
        for i in range(num_lanes):
            y_start = margin_top + i * lane_height
            y_end = margin_top + (i + 1) * lane_height
            
            # 마지막 차선은 하단 여백까지
            if i == num_lanes - 1:
                y_end = self.frame_height - margin_bottom
            
            self.lanes.append((y_start, y_end))
            
            # 카운팅 라인을 차선 중앙에 배치
            counting_y = (y_start + y_end) // 2
            self.counting_lines.append(counting_y)
            
            # 차선 이름
            self.lane_names.append(f"Lane {i + 1}")
        
        logging.info(f"자동 차선 설정 완료: {num_lanes}개 차선")
        return True
    
    def setup_custom_lanes(self, lane_configs: List[Tuple[int, int]]) -> bool:
        """
        사용자 정의 차선 설정
        
        Args:
            lane_configs (List[Tuple]): [(y_start, y_end), ...] 차선 좌표 리스트
            
        Returns:
            bool: 설정 성공 여부
        """
        if not lane_configs:
            logging.error("차선 설정이 비어있습니다")
            return False
        
        # 검증
        if not self._validate_lane_configs(lane_configs):
            return False
        
        self.lanes = lane_configs.copy()
        self.counting_lines = []
        self.lane_names = []
        
        for i, (y_start, y_end) in enumerate(self.lanes):
            # 카운팅 라인을 차선 중앙에 배치
            counting_y = (y_start + y_end) // 2
            self.counting_lines.append(counting_y)
            
            # 차선 이름
            self.lane_names.append(f"Lane {i + 1}")
        
        logging.info(f"사용자 정의 차선 설정 완료: {len(lane_configs)}개 차선")
        return True
    
    def setup_diagonal_lanes(self, num_lanes: int, angle: float = 15) -> bool:
        """
        대각선 차선 설정
        
        Args:
            num_lanes (int): 차선 수
            angle (float): 기울기 각도 (도)
            
        Returns:
            bool: 설정 성공 여부
        """
        # TODO: 대각선 차선 지원 (현재는 수평 차선만 지원)
        logging.warning("대각선 차선은 현재 지원되지 않습니다")
        return self.setup_auto_lanes(num_lanes)
    
    def _validate_lane_configs(self, lane_configs: List[Tuple[int, int]]) -> bool:
        """차선 설정 검증"""
        for i, (y_start, y_end) in enumerate(lane_configs):
            # 범위 체크
            if y_start < 0 or y_end > self.frame_height:
                logging.error(f"차선 {i+1}의 범위가 프레임을 벗어남: ({y_start}, {y_end})")
                return False
            
            # 시작점이 끝점보다 작은지 체크
            if y_start >= y_end:
                logging.error(f"차선 {i+1}의 시작점이 끝점보다 큼: ({y_start}, {y_end})")
                return False
            
            # 다른 차선과 겹치는지 체크
            for j, (other_start, other_end) in enumerate(lane_configs[i+1:], i+1):
                if not (y_end <= other_start or other_end <= y_start):
                    logging.error(f"차선 {i+1}과 차선 {j+1}이 겹침")
                    return False
        
        return True
    
    def get_vehicle_lane(self, center: Tuple[int, int]) -> int:
        """
        차량이 속한 차선 번호 반환
        
        Args:
            center (Tuple[int, int]): 차량 중심 좌표 (x, y)
            
        Returns:
            int: 차선 번호 (0부터 시작, -1은 차선 밖)
        """
        x, y = center
        
        for i, (lane_start, lane_end) in enumerate(self.lanes):
            if lane_start <= y <= lane_end:
                return i
        
        return -1  # 차선 밖
    
    def get_vehicle_lane_info(self, center: Tuple[int, int]) -> Dict:
        """
        차량의 차선 정보 반환
        
        Args:
            center (Tuple[int, int]): 차량 중심 좌표
            
        Returns:
            Dict: 차선 정보
        """
        lane_idx = self.get_vehicle_lane(center)
        
        if lane_idx == -1:
            return {
                'lane_index': -1,
                'lane_name': 'Outside',
                'lane_bounds': None,
                'counting_line': None,
                'distance_to_counting_line': None
            }
        
        lane_start, lane_end = self.lanes[lane_idx]
        counting_line = self.counting_lines[lane_idx]
        
        return {
            'lane_index': lane_idx,
            'lane_name': self.lane_names[lane_idx],
            'lane_bounds': (lane_start, lane_end),
            'counting_line': counting_line,
            'distance_to_counting_line': abs(center[1] - counting_line)
        }
    
    def check_line_crossing(self, prev_y: int, curr_y: int, lane_idx: int) -> Optional[str]:
        """
        카운팅 라인 통과 확인
        
        Args:
            prev_y (int): 이전 Y 좌표
            curr_y (int): 현재 Y 좌표
            lane_idx (int): 차선 인덱스
            
        Returns:
            Optional[str]: 통과 방향 ('up', 'down', None)
        """
        if lane_idx < 0 or lane_idx >= len(self.counting_lines):
            return None
        
        counting_line = self.counting_lines[lane_idx]
        
        # 위에서 아래로 통과
        if prev_y < counting_line <= curr_y:
            return 'down'
        
        # 아래에서 위로 통과
        if prev_y > counting_line >= curr_y:
            return 'up'
        
        return None
    
    def draw_lanes(self, frame: np.ndarray, show_names: bool = True, 
                  show_counting_lines: bool = True) -> np.ndarray:
        """
        차선을 프레임에 그리기
        
        Args:
            frame (np.ndarray): 프레임
            show_names (bool): 차선 이름 표시 여부
            show_counting_lines (bool): 카운팅 라인 표시 여부
            
        Returns:
            np.ndarray: 그려진 프레임
        """
        result_frame = frame.copy()
        
        # 차선 경계선 그리기
        for i, (y_start, y_end) in enumerate(self.lanes):
            # 상단 경계선 (첫 번째 차선 제외)
            if i > 0:
                cv2.line(result_frame, (0, y_start), (self.frame_width, y_start),
                        self.colors['lane_line'], self.line_thickness['lane_line'])
            
            # 하단 경계선 (마지막 차선만)
            if i == len(self.lanes) - 1:
                cv2.line(result_frame, (0, y_end), (self.frame_width, y_end),
                        self.colors['lane_line'], self.line_thickness['lane_line'])
            
            # 차선 이름 표시
            if show_names:
                text_y = y_start + 30
                cv2.putText(result_frame, self.lane_names[i], (10, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.colors['lane_number'],
                           self.line_thickness['lane_number'])
        
        # 카운팅 라인 그리기
        if show_counting_lines:
            for counting_y in self.counting_lines:
                cv2.line(result_frame, (0, counting_y), (self.frame_width, counting_y),
                        self.colors['counting_line'], self.line_thickness['counting_line'])
        
        return result_frame
    
    def draw_roi(self, frame: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        관심 영역(ROI) 그리기
        
        Args:
            frame (np.ndarray): 프레임
            roi (Tuple): (x1, y1, x2, y2) 관심 영역
            
        Returns:
            np.ndarray: 그려진 프레임
        """
        result_frame = frame.copy()
        x1, y1, x2, y2 = roi
        
        # ROI 경계 그리기
        cv2.rectangle(result_frame, (x1, y1), (x2, y2), 
                     self.colors['roi_boundary'], 3)
        
        # ROI 라벨
        cv2.putText(result_frame, "ROI", (x1 + 5, y1 + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['roi_boundary'], 2)
        
        return result_frame
    
    def get_lane_stats(self) -> Dict:
        """차선 통계 정보 반환"""
        if not self.lanes:
            return {}
        
        lane_heights = [end - start for start, end in self.lanes]
        
        return {
            'num_lanes': len(self.lanes),
            'frame_size': (self.frame_width, self.frame_height),
            'lane_heights': lane_heights,
            'avg_lane_height': sum(lane_heights) / len(lane_heights),
            'min_lane_height': min(lane_heights),
            'max_lane_height': max(lane_heights),
            'total_coverage': sum(lane_heights) / self.frame_height * 100
        }
    
    def export_config(self, filename: str = "lane_config.json"):
        """차선 설정을 파일로 내보내기"""
        config = {
            'frame_size': {
                'width': self.frame_width,
                'height': self.frame_height
            },
            'lanes': self.lanes,
            'counting_lines': self.counting_lines,
            'lane_names': self.lane_names,
            'colors': self.colors,
            'line_thickness': self.line_thickness
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"차선 설정 내보내기 완료: {filename}")
    
    def import_config(self, filename: str) -> bool:
        """파일에서 차선 설정 가져오기"""
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            
            # 프레임 크기 업데이트
            frame_size = config.get('frame_size', {})
            self.frame_width = frame_size.get('width', self.frame_width)
            self.frame_height = frame_size.get('height', self.frame_height)
            
            # 차선 설정
            self.lanes = config.get('lanes', [])
            self.counting_lines = config.get('counting_lines', [])
            self.lane_names = config.get('lane_names', [])
            
            # 시각화 설정
            if 'colors' in config:
                self.colors.update(config['colors'])
            if 'line_thickness' in config:
                self.line_thickness.update(config['line_thickness'])
            
            logging.info(f"차선 설정 가져오기 완료: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"차선 설정 가져오기 실패: {e}")
            return False
    
    def update_frame_size(self, width: int, height: int):
        """프레임 크기 업데이트"""
        old_width, old_height = self.frame_width, self.frame_height
        self.frame_width = width
        self.frame_height = height
        
        # 차선 좌표 스케일링 (높이 기준)
        if old_height != height and self.lanes:
            scale_factor = height / old_height
            
            self.lanes = [
                (int(start * scale_factor), int(end * scale_factor))
                for start, end in self.lanes
            ]
            
            self.counting_lines = [
                int(line * scale_factor) for line in self.counting_lines
            ]
        
        logging.info(f"프레임 크기 업데이트: {old_width}x{old_height} -> {width}x{height}")
    
    def get_lane_polygons(self) -> List[np.ndarray]:
        """각 차선의 폴리곤 반환 (고급 차선 감지용)"""
        polygons = []
        
        for y_start, y_end in self.lanes:
            # 사각형 폴리곤 생성
            polygon = np.array([
                [0, y_start],
                [self.frame_width, y_start],
                [self.frame_width, y_end],
                [0, y_end]
            ], dtype=np.int32)
            
            polygons.append(polygon)
        
        return polygons
    
    def reset(self):
        """차선 설정 초기화"""
        self.lanes = []
        self.counting_lines = []
        self.lane_names = []
        logging.info("차선 설정 초기화 완료")


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 차선 관리자 생성
    lane_manager = LaneManager(1920, 1080)
    
    # 자동 차선 설정 테스트
    success = lane_manager.setup_auto_lanes(3)
    print(f"자동 차선 설정 성공: {success}")
    
    # 차선 정보 확인
    print(f"차선 통계: {lane_manager.get_lane_stats()}")
    
    # 차량 위치 테스트
    test_center = (500, 400)
    lane_info = lane_manager.get_vehicle_lane_info(test_center)
    print(f"차량 위치 {test_center}의 차선 정보: {lane_info}")
    
    # 설정 내보내기 테스트
    lane_manager.export_config("test_lane_config.json")
