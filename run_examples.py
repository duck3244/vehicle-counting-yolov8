#!/usr/bin/env python3
"""
실행 예제 모음
다양한 시나리오별 사용 예제
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 모듈 추가
sys.path.append(str(Path(__file__).parent))

from main_system import VehicleCountingSystem


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('examples.log')
        ]
    )


def example_basic_video_processing():
    """예제 1: 기본 비디오 처리"""
    print("\n=== 예제 1: 기본 비디오 처리 ===")
    
    # 기본 설정으로 시스템 생성
    system = VehicleCountingSystem()
    
    # 설정 오버라이드
    config_override = {
        'model': {
            'path': 'yolov8n.pt',  # 빠른 처리를 위한 nano 모델
            'confidence_threshold': 0.5
        },
        'lanes': {
            'mode': 'auto',
            'count': 3
        },
        'video': {
            'display_realtime': True,
            'save_output': True
        },
        'output': {
            'save_results': True
        }
    }
    
    system.update_config(config_override)
    
    # 테스트 비디오 파일 확인
    test_videos = ['test_video.mp4', 'sample_traffic.mp4', 'highway.mp4']
    input_video = None
    
    for video in test_videos:
        if os.path.exists(video):
            input_video = video
            break
    
    if not input_video:
        print("테스트 비디오 파일이 없습니다. 다음 중 하나를 준비해주세요:")
        for video in test_videos:
            print(f"  - {video}")
        return False
    
    print(f"처리할 비디오: {input_video}")
    
    # 비디오 처리 실행
    success = system.process_video(input_video, "output_basic.mp4")
    
    if success:
        print("✓ 기본 비디오 처리 완료")
        print("  출력 파일: output_basic.mp4")
        print("  결과 파일: counting_results.json")
    else:
        print("✗ 기본 비디오 처리 실패")
    
    return success


def example_high_accuracy_processing():
    """예제 2: 고정밀도 처리"""
    print("\n=== 예제 2: 고정밀도 처리 ===")
    
    system = VehicleCountingSystem()
    
    # 고정밀도 설정
    config_override = {
        'model': {
            'path': 'yolov8m.pt',  # 중간 크기 모델로 정확도 향상
            'confidence_threshold': 0.7  # 높은 신뢰도 임계값
        },
        'tracking': {
            'max_history_length': 100,  # 긴 추적 히스토리
            'max_disappeared': 50
        },
        'counting': {
            'min_track_length': 10,  # 더 긴 추적 길이 요구
            'confidence_threshold': 0.7
        },
        'lanes': {
            'mode': 'auto',
            'count': 4
        }
    }
    
    system.update_config(config_override)
    
    # 비디오 파일 확인
    input_video = "highway_traffic.mp4"
    if not os.path.exists(input_video):
        print(f"테스트 비디오 파일이 없습니다: {input_video}")
        return False
    
    success = system.process_video(input_video, "output_high_accuracy.mp4")
    
    if success:
        print("✓ 고정밀도 처리 완료")
    else:
        print("✗ 고정밀도 처리 실패")
    
    return success


def example_custom_lanes():
    """예제 3: 사용자 정의 차선"""
    print("\n=== 예제 3: 사용자 정의 차선 ===")
    
    system = VehicleCountingSystem()
    
    # 사용자 정의 차선 설정
    config_override = {
        'lanes': {
            'mode': 'custom',
            'custom_lanes': [
                [0, 180],      # 차선 1: 상단
                [180, 360],    # 차선 2: 중상단
                [360, 540],    # 차선 3: 중하단
                [540, 720],    # 차선 4: 하단
                [720, 900]     # 차선 5: 최하단
            ]
        },
        'counting': {
            'directions': ['down']  # 아래쪽 방향만 카운팅
        }
    }
    
    system.update_config(config_override)
    
    # 비디오 처리
    input_video = "multi_lane_highway.mp4"
    if not os.path.exists(input_video):
        print(f"테스트 비디오 파일이 없습니다: {input_video}")
        # 기본 파일로 대체
        input_video = "test_video.mp4"
        if not os.path.exists(input_video):
            print("테스트 비디오 파일이 없습니다.")
            return False
    
    success = system.process_video(input_video, "output_custom_lanes.mp4")
    
    if success:
        print("✓ 사용자 정의 차선 처리 완료")
    else:
        print("✗ 사용자 정의 차선 처리 실패")
    
    return success


def example_webcam_realtime():
    """예제 4: 웹캠 실시간 처리"""
    print("\n=== 예제 4: 웹캠 실시간 처리 ===")
    print("웹캠을 사용한 실시간 처리를 시작합니다.")
    print("'q'를 눌러 종료, 'r'을 눌러 카운트 리셋, 's'를 눌러 스크린샷 저장")
    
    system = VehicleCountingSystem()
    
    # 실시간 처리에 최적화된 설정
    config_override = {
        'model': {
            'path': 'yolov8n.pt',  # 빠른 처리를 위한 nano 모델
            'confidence_threshold': 0.4  # 실시간에서는 낮은 임계값
        },
        'lanes': {
            'mode': 'auto',
            'count': 2  # 웹캠은 보통 2차선 정도
        },
        'tracking': {
            'max_history_length': 30,  # 짧은 히스토리
            'max_disappeared': 20
        }
    }
    
    system.update_config(config_override)
    
    try:
        success = system.process_webcam(camera_index=0)
        
        if success:
            print("✓ 웹캠 실시간 처리 완료")
        else:
            print("✗ 웹캠 실시간 처리 실패")
        
        return success
    
    except Exception as e:
        print(f"웹캠 처리 중 오류: {e}")
        return False


def example_batch_processing():
    """예제 5: 일괄 처리"""
    print("\n=== 예제 5: 일괄 처리 ===")
    
    # 처리할 비디오 목록
    video_configs = [
        {
            'input': 'video1.mp4',
            'output': 'output_video1.mp4',
            'lanes': 3,
            'model': 'yolov8n.pt'
        },
        {
            'input': 'video2.mp4', 
            'output': 'output_video2.mp4',
            'lanes': 4,
            'model': 'yolov8s.pt'
        },
        {
            'input': 'video3.mp4',
            'output': 'output_video3.mp4',
            'lanes': 2,
            'model': 'yolov8n.pt'
        }
    ]
    
    results = []
    
    for i, config in enumerate(video_configs):
        print(f"\n비디오 {i+1}/{len(video_configs)} 처리 중: {config['input']}")
        
        # 파일 존재 확인
        if not os.path.exists(config['input']):
            print(f"  파일이 없습니다: {config['input']}")
            results.append(False)
            continue
        
        # 시스템 초기화
        system = VehicleCountingSystem()
        
        # 개별 설정 적용
        config_override = {
            'model': {
                'path': config['model'],
                'confidence_threshold': 0.5
            },
            'lanes': {
                'mode': 'auto',
                'count': config['lanes']
            },
            'video': {
                'display_realtime': False  # 일괄 처리시 화면 표시 안함
            },
            'output': {
                'save_results': True,
                'results_file': f"results_video{i+1}"
            }
        }
        
        system.update_config(config_override)
        
        # 처리 실행
        success = system.process_video(config['input'], config['output'])
        results.append(success)
        
        if success:
            print(f"  ✓ {config['input']} 처리 완료")
        else:
            print(f"  ✗ {config['input']} 처리 실패")
    
    # 결과 요약
    success_count = sum(results)
    total_count = len(results)
    print(f"\n일괄 처리 완료: {success_count}/{total_count} 성공")
    
    return success_count == total_count


def example_performance_comparison():
    """예제 6: 성능 비교"""
    print("\n=== 예제 6: 모델 성능 비교 ===")
    
    models = [
        ('yolov8n.pt', '나노 모델'),
        ('yolov8s.pt', '소형 모델'),
        ('yolov8m.pt', '중형 모델')
    ]
    
    test_video = "test_short.mp4"  # 짧은 테스트 비디오
    
    if not os.path.exists(test_video):
        print(f"테스트 비디오가 없습니다: {test_video}")
        return False
    
    results = {}
    
    for model_path, model_name in models:
        print(f"\n{model_name} 테스트 중...")
        
        system = VehicleCountingSystem()
        
        config_override = {
            'model': {
                'path': model_path,
                'confidence_threshold': 0.5
            },
            'lanes': {
                'mode': 'auto',
                'count': 3
            },
            'video': {
                'display_realtime': False
            },
            'output': {
                'save_results': False
            }
        }
        
        system.update_config(config_override)
        
        import time
        start_time = time.time()
        
        try:
            success = system.process_video(test_video, None)
            end_time = time.time()
            
            if success:
                processing_time = end_time - start_time
                status = system.get_system_status()
                
                results[model_name] = {
                    'processing_time': processing_time,
                    'avg_fps': status.get('avg_fps', 0),
                    'total_vehicles': status.get('total_vehicles', 0),
                    'success': True
                }
                
                print(f"  ✓ 처리 시간: {processing_time:.2f}초")
                print(f"  ✓ 평균 FPS: {status.get('avg_fps', 0):.1f}")
                print(f"  ✓ 감지 차량: {status.get('total_vehicles', 0)}대")
            else:
                results[model_name] = {'success': False}
                print(f"  ✗ 처리 실패")
        
        except Exception as e:
            results[model_name] = {'success': False, 'error': str(e)}
            print(f"  ✗ 오류: {e}")
    
    # 결과 비교 출력
    print("\n=== 성능 비교 결과 ===")
    print(f"{'모델':<12} {'처리시간(초)':<12} {'평균 FPS':<10} {'감지 차량':<8}")
    print("-" * 45)
    
    for model_name, result in results.items():
        if result.get('success'):
            print(f"{model_name:<12} {result['processing_time']:<12.2f} "
                  f"{result['avg_fps']:<10.1f} {result['total_vehicles']:<8}")
        else:
            print(f"{model_name:<12} {'실패':<12} {'-':<10} {'-':<8}")
    
    return True


def example_configuration_showcase():
    """예제 7: 다양한 설정 시연"""
    print("\n=== 예제 7: 다양한 설정 시연 ===")
    
    configurations = [
        {
            'name': '교통량 많은 고속도로',
            'config': {
                'model': {'path': 'yolov8m.pt', 'confidence_threshold': 0.7},
                'lanes': {'mode': 'auto', 'count': 5},
                'counting': {'directions': ['both'], 'min_track_length': 8}
            }
        },
        {
            'name': '도심 교차로',
            'config': {
                'model': {'path': 'yolov8s.pt', 'confidence_threshold': 0.6},
                'lanes': {'mode': 'auto', 'count': 3},
                'counting': {'directions': ['down'], 'min_track_length': 5}
            }
        },
        {
            'name': '주차장 입구',
            'config': {
                'model': {'path': 'yolov8n.pt', 'confidence_threshold': 0.5},
                'lanes': {'mode': 'auto', 'count': 2},
                'counting': {'directions': ['up'], 'min_track_length': 3}
            }
        }
    ]
    
    test_video = "test_video.mp4"
    if not os.path.exists(test_video):
        print(f"테스트 비디오가 없습니다: {test_video}")
        return False
    
    for i, setup in enumerate(configurations):
        print(f"\n설정 {i+1}: {setup['name']}")
        
        system = VehicleCountingSystem()
        system.update_config(setup['config'])
        
        # 짧은 처리 (10초 정도)
        output_file = f"output_config_{i+1}.mp4"
        
        try:
            success = system.process_video(test_video, output_file)
            
            if success:
                status = system.get_system_status()
                print(f"  ✓ 처리 완료 - 감지 차량: {status.get('total_vehicles', 0)}대")
            else:
                print(f"  ✗ 처리 실패")
        
        except Exception as e:
            print(f"  ✗ 오류: {e}")
    
    return True


def main():
    """메인 함수"""
    setup_logging()
    
    print("YOLOv8 차선별 차량 카운팅 시스템 - 실행 예제")
    print("=" * 60)
    
    examples = [
        ("1", "기본 비디오 처리", example_basic_video_processing),
        ("2", "고정밀도 처리", example_high_accuracy_processing), 
        ("3", "사용자 정의 차선", example_custom_lanes),
        ("4", "웹캠 실시간 처리", example_webcam_realtime),
        ("5", "일괄 처리", example_batch_processing),
        ("6", "성능 비교", example_performance_comparison),
        ("7", "다양한 설정 시연", example_configuration_showcase),
        ("0", "모든 예제 실행", None)
    ]
    
    print("실행할 예제를 선택하세요:")
    for num, name, _ in examples:
        print(f"  {num}: {name}")
    
    try:
        choice = input("\n선택 (0-7): ").strip()
        
        if choice == "0":
            # 모든 예제 실행 (웹캠 제외)
            all_success = True
            for num, name, func in examples[:-1]:  # 마지막(모든 예제) 제외
                if func and num != "4":  # 웹캠 예제 제외
                    print(f"\n{'='*60}")
                    print(f"예제 {num} 실행 중: {name}")
                    print(f"{'='*60}")
                    
                    try:
                        success = func()
                        if not success:
                            all_success = False
                    except KeyboardInterrupt:
                        print("\n사용자에 의해 중단됨")
                        break
                    except Exception as e:
                        print(f"예제 실행 중 오류: {e}")
                        all_success = False
            
            print(f"\n{'='*60}")
            if all_success:
                print("모든 예제 실행 완료!")
            else:
                print("일부 예제 실행에 실패했습니다.")
        
        elif choice in [num for num, _, _ in examples[:-1]]:
            selected_example = next((func for num, _, func in examples if num == choice), None)
            if selected_example:
                success = selected_example()
                if success:
                    print(f"\n예제 {choice} 실행 완료!")
                else:
                    print(f"\n예제 {choice} 실행 실패!")
        else:
            print("잘못된 선택입니다.")
    
    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램이 중단되었습니다.")
    
    except Exception as e:
        print(f"프로그램 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
