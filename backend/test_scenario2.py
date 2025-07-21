#!/usr/bin/env python3
"""
시나리오 2 파싱 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.parser import input_parser

def test_scenario2():
    """시나리오 2 파싱 테스트"""
    
    test_cases = [
        '44043-CA1-6"-P',
        '44043-CA1-6"-P, Leak 볼팅 작업',
        'Y-MV1035. 고장',
        'SW-CV1307-02, 1창고 #7Line, 컨베이어 러버벨트, 소음 발생, 우선작업'
    ]
    
    print("=== 시나리오 2 파싱 테스트 ===\n")
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"테스트 {i}: {test_input}")
        
        # 시나리오 판단
        scenario = input_parser._determine_scenario(test_input)
        print(f"  시나리오: {scenario}")
        
        # 파싱 결과
        parsed = input_parser.parse_input(test_input)
        print(f"  결과: scenario={parsed.scenario}, itemno={parsed.itemno}, status_code={parsed.status_code}")
        
        # 컨텍스트 파싱 테스트 (우회 확인)
        context_parsed = input_parser.parse_input_with_context(test_input, session_id="test_session")
        print(f"  컨텍스트 파싱: scenario={context_parsed.scenario}, itemno={context_parsed.itemno}")
        
        print()

if __name__ == "__main__":
    test_scenario2() 