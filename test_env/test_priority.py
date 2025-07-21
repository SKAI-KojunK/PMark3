#!/usr/bin/env python3
"""
우선순위 처리 로직 테스트 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.agents.parser import input_parser
from backend.app.logic.recommender import recommender
from backend.app.database import DatabaseManager

def test_priority_handling():
    """우선순위 처리 테스트"""
    print("=" * 60)
    print("우선순위 처리 로직 테스트")
    print("=" * 60)
    
    # 테스트 케이스 1: 우선순위 언급 없음
    print("\n1. 우선순위 언급 없는 경우:")
    user_input = "1PE 압력베젤 고장"
    parsed = input_parser.parse_input(user_input)
    print(f"   입력: {user_input}")
    print(f"   파싱 결과 우선순위: {parsed.priority}")
    
    # 추천 시스템에서 처리
    recommendations = recommender.get_recommendations(parsed, limit=3)
    if recommendations:
        print(f"   추천 결과 우선순위: {recommendations[0].priority}")
    else:
        print("   추천 결과 없음")
    
    # 테스트 케이스 2: 우선순위 명시적 언급
    print("\n2. 우선순위 명시적 언급:")
    user_input = "긴급하게 2PE 펌프 고장"
    parsed = input_parser.parse_input(user_input)
    print(f"   입력: {user_input}")
    print(f"   파싱 결과 우선순위: {parsed.priority}")
    
    # 추천 시스템에서 처리
    recommendations = recommender.get_recommendations(parsed, limit=3)
    if recommendations:
        print(f"   추천 결과 우선순위: {recommendations[0].priority}")
    else:
        print("   추천 결과 없음")
    
    # 테스트 케이스 3: ITEMNO 기반 조회
    print("\n3. ITEMNO 기반 조회:")
    user_input = "44043-CA1-6-P"
    parsed = input_parser.parse_input(user_input)
    print(f"   입력: {user_input}")
    print(f"   파싱 결과 우선순위: {parsed.priority}")
    print(f"   시나리오: {parsed.scenario}")
    
    # 추천 시스템에서 처리
    recommendations = recommender.get_recommendations(parsed, limit=3)
    if recommendations:
        print(f"   추천 결과 우선순위: {recommendations[0].priority}")
    else:
        print("   추천 결과 없음")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_priority_handling() 