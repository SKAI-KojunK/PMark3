#!/usr/bin/env python3
"""
PMark2.5 자동완성 기능 테스트 스크립트
"""

import requests
import json
import time

# 테스트 환경 백엔드 URL
BASE_URL = "http://localhost:8010/api/v1"

def test_scenario_analysis():
    """시나리오 분석 기능 테스트"""
    print("🔍 시나리오 분석 테스트")
    print("=" * 50)
    
    test_cases = [
        # 시나리오 1 테스트 케이스
        ("설비유형 Pressure Vessel", "scenario1"),
        ("equipment type Heat Exchanger", "scenario1"),
        ("설비 분류 카테고리", "scenario1"),
        
        # 시나리오 2 테스트 케이스
        ("44043-CA1-6\"-P, Leak 볼팅 작업", "scenario2"),
        ("Y-MV1035. 고장", "scenario2"),
        ("SW-CV1307-02, 컨베이어 러버벨트, 소음 발생", "scenario2"),
        ("RFCC, 44043-CA1-6\"-P, P4407A DIS' CHECK V/V FLANGE LEAK BOLTING 작업", "scenario2"),
        
        # 모호한 케이스
        ("Pressure Vessel", "unknown"),
        ("44043", "unknown"),
    ]
    
    for input_text, expected_scenario in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/analyze-scenario",
                json={"input_text": input_text},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                actual_scenario = result["scenario_type"]
                confidence = result["confidence"]
                reasoning = result["reasoning"]
                
                status = "✅" if actual_scenario == expected_scenario else "❌"
                print(f"{status} 입력: {input_text}")
                print(f"   예상: {expected_scenario}, 실제: {actual_scenario}, 신뢰도: {confidence:.2f}")
                print(f"   근거: {reasoning}")
                print()
            else:
                print(f"❌ 오류: {response.status_code} - {response.text}")
                print()
                
        except Exception as e:
            print(f"❌ 예외: {input_text} - {str(e)}")
            print()

def test_autocomplete():
    """자동완성 기능 테스트"""
    print("🔍 자동완성 기능 테스트")
    print("=" * 50)
    
    test_cases = [
        # 시나리오 1 자동완성 테스트
        ("Pressure", "scenario1"),
        ("Heat", "scenario1"),
        ("Valve", "scenario1"),
        ("Pump", "scenario1"),
        
        # 시나리오 2 자동완성 테스트
        ("44043", "scenario2"),
        ("Y-MV", "scenario2"),
        ("SW-CV", "scenario2"),
        ("RFCC", "scenario2"),
        
        # 모호한 케이스
        ("MV", "unknown"),
        ("CV", "unknown"),
    ]
    
    for input_text, expected_scenario in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/autocomplete",
                json={"input_text": input_text},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                suggestions = result["suggestions"]
                scenario_type = result["scenario_type"]
                confidence = result["confidence"]
                
                print(f"📝 입력: {input_text}")
                print(f"   시나리오: {scenario_type}, 신뢰도: {confidence:.2f}")
                print(f"   추천 개수: {len(suggestions)}")
                
                if suggestions:
                    print("   추천 목록:")
                    for i, suggestion in enumerate(suggestions[:5], 1):  # 최대 5개만 표시
                        print(f"     {i}. {suggestion}")
                else:
                    print("   추천 없음")
                print()
            else:
                print(f"❌ 오류: {response.status_code} - {response.text}")
                print()
                
        except Exception as e:
            print(f"❌ 예외: {input_text} - {str(e)}")
            print()

def test_backend_health():
    """백엔드 상태 확인"""
    print("🏥 백엔드 상태 확인")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 백엔드 정상 동작")
            print(f"   응답: {response.json()}")
        else:
            print(f"❌ 백엔드 오류: {response.status_code}")
    except Exception as e:
        print(f"❌ 백엔드 연결 실패: {str(e)}")
    
    print()

def main():
    """메인 테스트 함수"""
    print("🚀 PMark2.5 자동완성 기능 테스트 시작")
    print("=" * 60)
    print()
    
    # 백엔드 상태 확인
    test_backend_health()
    
    # 잠시 대기 (백엔드 시작 시간 고려)
    print("⏳ 백엔드 준비 대기 중...")
    time.sleep(3)
    
    # 시나리오 분석 테스트
    test_scenario_analysis()
    
    # 자동완성 테스트
    test_autocomplete()
    
    print("✅ 테스트 완료")

if __name__ == "__main__":
    main() 