"""
차량 감지 모듈
YOLOv8을 사용한 차량 감지 기능
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Dict, Optional
import logging


class VehicleDetector:
    """YOLOv8 기반 차량 감지 클래스"""
    
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5, 
                 device: str = "auto"):
        """
        차량 감지기 초기화
        
        Args:
            model_path (str): YOLOv8 모델 경로
            conf_threshold (float): 신뢰도 임계값
            device (str): 디바이스 (auto, cpu, cuda)
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.device = device
        
        # COCO 데이터셋의 차량 클래스 ID
        self.vehicle_classes = {
            2: 'car',
            3: 'motorcycle', 
            5: 'bus',
            7: 'truck'
        }
        
        # 모델 로드
        self.model = self._load_model()
        
        # 통계
        self.detection_stats = {
            'total_detections': 0,
            'frames_processed': 0,
            'detections_by_class': {name: 0 for name in self.vehicle_classes.values()}
        }
        
        logging.info(f"VehicleDetector 초기화 완료: {model_path}")
    
    def _load_model(self) -> YOLO:
        """YOLO 모델 로드"""
        try:
            model = YOLO(self.model_path)
            
            # 디바이스 설정
            if self.device != "auto":
                model.to(self.device)
            
            logging.info(f"YOLO 모델 로드 성공: {self.model_path}")
            return model
            
        except Exception as e:
            logging.error(f"모델 로드 실패: {e}")
            raise
    
    def detect_vehicles(self, frame: np.ndarray, track: bool = False) -> List[Dict]:
        """
        프레임에서 차량 감지
        
        Args:
            frame (np.ndarray): 입력 프레임
            track (bool): 추적 사용 여부
            
        Returns:
            List[Dict]: 감지된 차량 정보 리스트
        """
        self.detection_stats['frames_processed'] += 1
        
        try:
            # YOLO 추론
            if track:
                results = self.model.track(frame, persist=True, conf=self.conf_threshold)
            else:
                results = self.model(frame, conf=self.conf_threshold)
            
            vehicles = self._process_results(results)
            
            # 통계 업데이트
            self.detection_stats['total_detections'] += len(vehicles)
            for vehicle in vehicles:
                class_name = vehicle['class_name']
                if class_name in self.detection_stats['detections_by_class']:
                    self.detection_stats['detections_by_class'][class_name] += 1
            
            return vehicles
            
        except Exception as e:
            logging.error(f"차량 감지 오류: {e}")
            return []
    
    def _process_results(self, results) -> List[Dict]:
        """
        YOLO 결과 처리
        
        Args:
            results: YOLO 추론 결과
            
        Returns:
            List[Dict]: 처리된 차량 정보
        """
        vehicles = []
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
                
            for box in boxes:
                # 신뢰도 확인
                conf = float(box.conf.cpu().numpy()[0])
                if conf < self.conf_threshold:
                    continue
                
                # 클래스 확인 (차량만)
                class_id = int(box.cls.cpu().numpy()[0])
                if class_id not in self.vehicle_classes:
                    continue
                
                # 바운딩 박스 좌표
                x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
                
                # 추적 ID 추출 (있는 경우)
                track_id = None
                if hasattr(box, 'id') and box.id is not None:
                    track_id = int(box.id.cpu().numpy()[0])
                
                # 차량 정보 생성
                vehicle_info = {
                    'bbox': (x1, y1, x2, y2),
                    'confidence': conf,
                    'class_id': class_id,
                    'class_name': self.vehicle_classes[class_id],
                    'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                    'area': (x2 - x1) * (y2 - y1),
                    'track_id': track_id
                }
                
                vehicles.append(vehicle_info)
        
        return vehicles
    
    def filter_by_size(self, vehicles: List[Dict], 
                      min_area: int = 400, max_area: int = 50000) -> List[Dict]:
        """
        크기 기준으로 차량 필터링
        
        Args:
            vehicles (List[Dict]): 차량 리스트
            min_area (int): 최소 면적
            max_area (int): 최대 면적
            
        Returns:
            List[Dict]: 필터링된 차량 리스트
        """
        return [v for v in vehicles if min_area <= v['area'] <= max_area]
    
    def filter_by_region(self, vehicles: List[Dict], 
                        region: Tuple[int, int, int, int]) -> List[Dict]:
        """
        영역 기준으로 차량 필터링
        
        Args:
            vehicles (List[Dict]): 차량 리스트
            region (Tuple): 관심 영역 (x1, y1, x2, y2)
            
        Returns:
            List[Dict]: 필터링된 차량 리스트
        """
        rx1, ry1, rx2, ry2 = region
        filtered_vehicles = []
        
        for vehicle in vehicles:
            center_x, center_y = vehicle['center']
            if rx1 <= center_x <= rx2 and ry1 <= center_y <= ry2:
                filtered_vehicles.append(vehicle)
        
        return filtered_vehicles
    
    def get_vehicle_crops(self, frame: np.ndarray, 
                         vehicles: List[Dict]) -> List[Tuple[np.ndarray, Dict]]:
        """
        차량 영역 크롭
        
        Args:
            frame (np.ndarray): 원본 프레임
            vehicles (List[Dict]): 차량 리스트
            
        Returns:
            List[Tuple]: (크롭된 이미지, 차량 정보) 튜플 리스트
        """
        crops = []
        
        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle['bbox']
            
            # 경계 확인
            h, w = frame.shape[:2]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            # 크롭
            if x2 > x1 and y2 > y1:
                crop = frame[y1:y2, x1:x2]
                crops.append((crop, vehicle))
        
        return crops
    
    def draw_detections(self, frame: np.ndarray, vehicles: List[Dict], 
                       show_confidence: bool = True, show_class: bool = True,
                       show_track_id: bool = True) -> np.ndarray:
        """
        감지 결과를 프레임에 그리기
        
        Args:
            frame (np.ndarray): 프레임
            vehicles (List[Dict]): 차량 리스트
            show_confidence (bool): 신뢰도 표시 여부
            show_class (bool): 클래스 표시 여부
            show_track_id (bool): 추적 ID 표시 여부
            
        Returns:
            np.ndarray: 그려진 프레임
        """
        result_frame = frame.copy()
        
        # 클래스별 색상 정의
        colors = {
            'car': (0, 255, 0),      # 초록색
            'truck': (255, 0, 0),    # 빨간색
            'bus': (0, 0, 255),      # 파란색
            'motorcycle': (255, 255, 0)  # 노란색
        }
        
        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle['bbox']
            class_name = vehicle['class_name']
            confidence = vehicle['confidence']
            track_id = vehicle['track_id']
            
            # 바운딩 박스 색상
            color = colors.get(class_name, (255, 255, 255))
            
            # 바운딩 박스 그리기
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)
            
            # 라벨 텍스트 구성
            label_parts = []
            if show_track_id and track_id is not None:
                label_parts.append(f"ID:{track_id}")
            if show_class:
                label_parts.append(class_name)
            if show_confidence:
                label_parts.append(f"{confidence:.2f}")
            
            label = " ".join(label_parts)
            
            # 라벨 배경
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(result_frame, (x1, y1 - text_height - 10), 
                         (x1 + text_width, y1), color, -1)
            
            # 라벨 텍스트
            cv2.putText(result_frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 중심점 표시
            center_x, center_y = vehicle['center']
            cv2.circle(result_frame, (center_x, center_y), 3, color, -1)
        
        return result_frame
    
    def get_detection_stats(self) -> Dict:
        """감지 통계 반환"""
        stats = self.detection_stats.copy()
        if stats['frames_processed'] > 0:
            stats['avg_detections_per_frame'] = (
                stats['total_detections'] / stats['frames_processed']
            )
        else:
            stats['avg_detections_per_frame'] = 0
        
        return stats
    
    def reset_stats(self):
        """통계 초기화"""
        self.detection_stats = {
            'total_detections': 0,
            'frames_processed': 0,
            'detections_by_class': {name: 0 for name in self.vehicle_classes.values()}
        }
        logging.info("감지 통계 초기화 완료")
    
    def update_confidence_threshold(self, new_threshold: float):
        """신뢰도 임계값 업데이트"""
        old_threshold = self.conf_threshold
        self.conf_threshold = new_threshold
        logging.info(f"신뢰도 임계값 변경: {old_threshold} -> {new_threshold}")
    
    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            'model_path': self.model_path,
            'confidence_threshold': self.conf_threshold,
            'device': self.device,
            'vehicle_classes': self.vehicle_classes,
            'model_type': 'YOLOv8'
        }


if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 감지기 초기화
    detector = VehicleDetector("yolov8n.pt", 0.5)
    
    # 테스트 이미지로 감지 테스트
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    vehicles = detector.detect_vehicles(test_frame)
    
    print(f"감지된 차량 수: {len(vehicles)}")
    print(f"모델 정보: {detector.get_model_info()}")
    print(f"감지 통계: {detector.get_detection_stats()}")
