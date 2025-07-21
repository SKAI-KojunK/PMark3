"""
PMark3 자연어 입력 파서 모듈

=== 모듈 개요 ===
사용자의 자연어 입력을 분석하여 구조화된 데이터로 변환하는 핵심 모듈입니다.
OpenAI GPT-4를 활용하여 시나리오 판단 및 정보 추출을 수행합니다.

=== Production 전환 주요 포인트 ===
🔄 LangGraph 노드 전환: 이 클래스는 LangGraph의 파싱 노드로 전환됩니다
🤖 로컬 LLM 연동: OpenAI → vLLM 기반 Mistral 7B/Qwen3 14B로 전환 예정
📊 성능 최적화: 배치 처리, 캐싱, 재시도 로직 추가 필요
🔍 벡터 검색 통합: 정규화 로직과 벡터 임베딩 시스템 연동 예정

=== 연계 시스템 ===
• 입력: chat.py (사용자 메시지) → session_manager.py (컨텍스트)
• 처리: normalizer.py (용어 정규화) → database.py (검증)  
• 출력: recommender.py (추천 엔진) → response_generator.py

=== AI 연구원 실험 포인트 ===
1. 프롬프트 엔지니어링: _create_scenario_1_prompt() 최적화
2. 모델 성능 비교: GPT-4 vs Mistral 7B vs Qwen3 14B
3. 시나리오 분기 로직: _determine_scenario() 개선
4. 정확도 측정: confidence 점수 산정 알고리즘 개선

=== 개발팀 참고사항 ===
• LangGraph 전환 시 각 메서드를 독립적인 노드로 분리
• Azure 배포 시 환경변수 기반 설정 관리 필요
• Production 모니터링: 파싱 정확도, 응답 시간, 에러율 추적
• 멀티턴 대화 지원: 세션 상태 관리 및 컨텍스트 누적 로직
"""

import re
from openai import OpenAI
from typing import Dict, List, Optional, Tuple
from ..config import Config
from ..models import ParsedInput
from ..logic.normalizer import normalizer
import json
from difflib import SequenceMatcher

class InputParser:
    """
    자연어 입력 파서 핵심 클래스
    
    === 현재 아키텍처에서의 역할 ===
    🎯 시나리오 판단: S1(자연어) vs S2(ITEMNO) vs S3(컨텍스트 기반)
    🔍 정보 추출: location, equipment_type, status_code, priority
    🤝 정규화 연동: normalizer.py와 협력하여 표준 용어 매핑
    📊 신뢰도 평가: 추출 결과의 confidence 점수 산정
    
    === Production 전환 시 변경사항 ===
    🔄 LangGraph 노드화:
    - parse_input_with_context() → parsing_node()
    - _determine_scenario() → scenario_router_node() 
    - 각 시나리오별 독립 노드 분리
    
    🤖 로컬 LLM 통합:
    - OpenAI 클라이언트 → vLLM 엔드포인트 호출
    - 배치 처리 지원 (동일 세션 내 다중 요청)
    - 자동 재시도 및 타임아웃 관리
    
    📈 성능 최적화:
    - 결과 캐싱 (Redis/Azure Cache 연동)
    - 응답 시간 모니터링 및 알림
    - 메모리 사용량 추적
    
    === 연계 지점 분석 ===
    ⬅️ 입력단: 
    - api/chat.py: chat_endpoint() → parse_input()
    - session_manager.py: 컨텍스트 정보 제공
    
    ➡️ 출력단:
    - logic/normalizer.py: _normalize_extracted_terms() 호출
    - logic/recommender.py: ParsedInput 객체 전달
    - database.py: 검색 필터 생성
    
    === AI 연구원 실험 가이드 ===
    📝 프롬프트 최적화: notebooks/01_parser_experiment.ipynb 활용
    🔬 모델 비교: GPT-4 vs Mistral 7B vs Qwen3 14B 성능 벤치마킹
    📊 정확도 측정: Ground Truth 데이터셋 기반 평가
    🎛️ 하이퍼파라미터: temperature, max_tokens, top_p 조정 실험
    
    === 개발팀 구현 가이드 ===
    🏗️ 아키텍처 설계:
    - 상태 관리: PMark3WorkflowState 활용
    - 에러 처리: 재시도 로직 및 폴백 메커니즘
    - 모니터링: 파싱 정확도, 응답 시간, 에러율 추적
    
    🚀 배포 고려사항:
    - 환경별 설정: dev/staging/prod 분리
    - 스케일링: HPA 기반 자동 확장
    - 보안: API 키 관리 (Azure Key Vault)
    """
    
    def __init__(self):
        """
        입력 파서 초기화
        
        설정:
        - OpenAI 클라이언트 초기화
        - 모델 설정
        """
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # ITEMNO 패턴 (채번 규칙)
        self.itemno_patterns = [
            r'\b[A-Z]{2,4}-\d{5}\b',  # 예: RFCC-00123
            r'\b[A-Z]-\w+\b',         # 예: Y-MV1035
            r'\b\d{5}-[A-Z]{2}-\d+-[A-Z]\b',  # 예: 44043-CA1-6-P
            r'\b\d{4,}-[A-Z]{2}-\d+-[A-Z]\b',  # 예: 44043-CA1-6-P (더 유연한 패턴)
            r'\b[A-Z]{2}-\w+-\d{2}\b',  # 예: SW-CV1307-02
        ]
        
        # 우선순위 키워드
        self.priority_keywords = {
            "긴급작업": ["긴급", "긴급작업", "urgent", "emergency"],
            "우선작업": ["우선", "우선작업", "priority", "high"],
            "일반작업": ["일반", "일반작업", "normal", "regular"]
        }
    
    def parse_input(self, user_input: str, conversation_history: list = None) -> ParsedInput:
        """
        사용자 입력을 파싱하여 구조화된 데이터로 변환
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            ParsedInput: 파싱된 구조화된 데이터
            
        사용처:
        - chat.py: chat_endpoint()에서 사용자 입력 분석
        - recommender.py: RecommendationEngine에서 파싱 결과 활용
        
        연계 파일:
        - models.py: ParsedInput 모델로 반환
        - logic/normalizer.py: _normalize_extracted_terms()에서 용어 정규화
        
        예시:
        - "1PE 압력베젤 고장" → ParsedInput(scenario="S1", location="No.1 PE", equipment_type="Pressure Vessel", status_code="고장")
        - "ITEMNO 12345 작업상세" → ParsedInput(scenario="S2", itemno="12345")
        
        담당자 수정 가이드:
        - 시나리오 판단 로직은 비즈니스 요구사항에 따라 조정
        - 새로운 필드 추출 시 _create_scenario_1_prompt() 수정 필요
        - confidence 점수는 LLM 응답의 신뢰도를 반영
        """
        try:
            # 시나리오 판단
            scenario = self._determine_scenario(user_input)
            
            if scenario == "S1":
                # 시나리오 1: 자연어로 작업 요청
                return self._parse_scenario_1(user_input)
            elif scenario == "S2":
                # 시나리오 2: ITEMNO로 작업 상세 요청
                return self._parse_scenario_2(user_input)
            else:
                # 기본 시나리오
                return self._parse_default_scenario(user_input)
                
        except Exception as e:
            print(f"입력 파싱 오류: {e}")
            # 오류 시 기본값 반환
            return ParsedInput(
                scenario="S1",
                location=None,
                equipment_type=None,
                status_code=None,
                priority=None,
                itemno=None,
                confidence=0.0
            )
    
    def parse_input_with_context(self, user_input: str, conversation_history: list = None, session_id: str = None) -> ParsedInput:
        """
        세션 컨텍스트를 포함한 입력 파싱 (PMark3 고급 기능)
        
        Args:
            user_input: 사용자 입력 메시지
            conversation_history: 대화 히스토리
            session_id: 세션 ID
            
        Returns:
            ParsedInput: 컨텍스트를 반영한 파싱 결과
        """
        try:
            # 세션 컨텍스트 로드
            from ..session_manager import session_manager
            session_state = session_manager.get_session(session_id) if session_id else None
            
            if session_state and session_state.accumulated_clues.has_any_clue():
                # 기존 누적 단서가 있을 때만 컨텍스트 파싱 사용
                return self._parse_scenario_1_with_context(user_input, conversation_history, session_state.accumulated_clues)
            else:
                # 첫 번째 입력이거나 누적 단서가 없으면 일반 파싱 사용
                print(f"누적 단서가 없어 일반 파싱 사용")
                return self.parse_input(user_input, conversation_history)
                
        except Exception as e:
            print(f"컨텍스트 파싱 오류: {e}")
            # 기본 파싱으로 fallback
            return self.parse_input(user_input, conversation_history)

    def _determine_scenario(self, user_input: str) -> str:
        """
        사용자 입력을 분석하여 시나리오 판단
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            시나리오 타입 ("S1", "S2", "default")
            
        판단 기준:
        - S1: 자연어로 작업 요청 (위치, 설비, 현상 등 포함)
        - S2: ITEMNO로 작업 상세 요청 (ITEMNO 포함)
        - default: 기타
        
        담당자 수정 가이드:
        - 시나리오 판단 기준은 비즈니스 요구사항에 따라 조정
        - 정규표현식 패턴 추가로 더 정확한 판단 가능
        """
        # ITEMNO 패턴 확인 (시나리오 2) - 더 정확한 패턴 매칭
        itemno_patterns = [
            r'ITEMNO\s*\d+',  # ITEMNO 12345
            r'\b\d{4,}-\w+',  # 44043-CA1-6-P
            r'\b[A-Z]-\w+\d+',  # Y-MV1035
            r'\b[A-Z]{2,4}-\w+',  # PE-SE1304B
            r'\b[A-Z]{2,4}\d+',  # SW-CV1307-02
            r'\b\d{5,}',  # 5자리 이상 숫자
            r'"[^"]*"',  # 따옴표로 둘러싸인 코드
        ]
        
        for pattern in itemno_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return "S2"
        
        # 자연어 작업 요청 패턴 확인 (시나리오 1)
        # 더 포괄적인 키워드 목록
        keywords = [
            '고장', '누설', '작동불량', '점검', '정비', '압력', '온도', '밸브', '펌프', '탱크',
            '베젤', '베셀', 'vessel', 'pressure', 'valve', 'motor', 'pump', 'tank',
            '컨베이어', 'conveyor', '열교환', 'heat', 'exchanger', '필터', 'filter',
            '압축', 'compressor', '팬', 'fan', '블로워', 'blower', '드럼', 'drum',
            '반응', 'reactor', '분석', 'analyzer', '누출', 'leak', 'bolting',
            '소음', '진동', '온도상승', '압력상승', '결함', '수명소진'
        ]
        
        if any(keyword.lower() in user_input.lower() for keyword in keywords):
            return "S1"
        
        # 기본값: 시나리오 1 (자연어 입력으로 가정)
        return "S1"
    
    def _parse_scenario_1(self, user_input: str, conversation_history: list = None) -> ParsedInput:
        """
        시나리오 1 파싱: 자연어로 작업 요청
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            ParsedInput: 파싱된 구조화된 데이터
            
        추출 정보:
        - location: 위치/공정
        - equipment_type: 설비유형
        - status_code: 현상코드
        - priority: 우선순위
        
        담당자 수정 가이드:
        - 추출 필드 변경 시 프롬프트 수정 필요
        - 대화 히스토리 활용 로직 개선 가능
        - 정규화 로직은 _normalize_extracted_terms()에서 처리
        """
        try:
            # LLM 프롬프트 생성
            prompt = self._create_scenario_1_prompt(user_input, conversation_history)
            
            # LLM 호출 (타임아웃 설정)
            import time
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 설비관리 시스템의 입력 분석 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 일관성을 위해 낮은 temperature
                max_tokens=500
            )
            
            # 타임아웃 체크
            if time.time() - start_time > 15:
                print("LLM 호출 타임아웃")
                return self._create_default_parsed_input()
            
            result_text = response.choices[0].message.content.strip()
            
            # 응답 파싱
            parsed_data = self._parse_llm_response(result_text)
            
            # 추출된 용어 정규화
            normalized_data = self._normalize_extracted_terms(parsed_data)
            
            return ParsedInput(
                scenario="S1",
                location=normalized_data.get('location'),
                equipment_type=normalized_data.get('equipment_type'),
                status_code=normalized_data.get('status_code'),
                priority=normalized_data.get('priority'),  # None일 수 있음 - 추후 DB에서 가져오거나 기본값 설정
                itemno=None,
                confidence=parsed_data.get('confidence', 0.0)
            )
            
        except Exception as e:
            print(f"시나리오 1 파싱 오류: {e}")
            return self._create_default_parsed_input()

    def _parse_scenario_1_with_context(self, user_input: str, conversation_history: list, accumulated_clues) -> ParsedInput:
        """
        누적된 단서와 함께 시나리오 1 파싱
        
        Args:
            user_input: 사용자 입력
            conversation_history: 대화 히스토리
            accumulated_clues: 누적된 단서들
            
        Returns:
            ParsedInput: 컨텍스트를 반영한 파싱 결과
        """
        try:
            print(f"컨텍스트 파싱 시작: {user_input[:50]}...")
            print(f"누적 단서 - 위치: {accumulated_clues.location}, 설비: {accumulated_clues.equipment_type}, 현상: {accumulated_clues.status_code}")
            
            # 컨텍스트 포함 프롬프트 생성
            prompt = self._create_scenario_1_context_prompt(user_input, conversation_history, accumulated_clues)
            
            # LLM 호출
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 설비관리 시스템의 멀티턴 대화 분석 전문가입니다. 이전 대화 컨텍스트를 고려하여 입력을 분석합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            print(f"LLM 응답: {result_text}")
            
            # 응답 파싱
            parsed_data = self._parse_llm_response(result_text)
            
            # 추출된 용어 정규화
            normalized_data = self._normalize_extracted_terms(parsed_data)
            
            # ParsedInput 객체 생성
            parsed_input = ParsedInput(
                scenario="S1",
                location=normalized_data.get("location"),
                equipment_type=normalized_data.get("equipment_type"),
                status_code=normalized_data.get("status_code"),
                priority=normalized_data.get("priority"),  # None일 수 있음 - 추후 DB에서 가져오거나 기본값 설정
                confidence=normalized_data.get("confidence", 0.8)
            )
            
            print(f"컨텍스트 파싱 완료: {parsed_input}")
            return parsed_input
            
        except Exception as e:
            print(f"컨텍스트 파싱 오류: {e}")
            import traceback
            traceback.print_exc()
            # 기본 파싱으로 fallback
            return self._parse_scenario_1(user_input, conversation_history)

    def _create_scenario_1_prompt(self, user_input: str, conversation_history: list = None) -> str:
        """
        시나리오 1용 LLM 프롬프트 생성
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            LLM 프롬프트 문자열
            
        담당자 수정 가이드:
        - 추출 필드 변경 시 이 프롬프트 수정 필요
        - 예시는 실제 사용 사례를 반영하여 업데이트
        - 대화 히스토리 활용 로직 개선 가능
        """
        
        # 대화 히스토리 컨텍스트 생성
        context = ""
        if conversation_history and len(conversation_history) > 0:
            context = "대화 히스토리:\n"
            for msg in conversation_history[-3:]:  # 최근 3개 메시지만 사용
                context += f"{msg['role']}: {msg['content']}\n"
            context += "\n"
        
        return f"""
{context}다음 사용자 입력에서 설비관리 작업 요청 관련 정보를 추출해주세요.

**사용자 입력**: {user_input}

**추출해야 할 정보**:
1. location: 위치/공정 (예: No.1 PE, No.2 PE, 석유제품배합/저장, 합성수지 포장, RFCC, 1창고 #7Line, 2창고 #8Line, 공통 시설)
   - 사용자가 "위치" 또는 "공정"으로 언급한 내용을 우선적으로 추출
   - 위치 정보가 없으면 공정명을 위치로 사용
2. equipment_type: 설비유형 (예: Pressure Vessel, Motor Operated Valve, Conveyor, Pump, Heat Exchanger, Valve, Control Valve, Tank, Storage Tank, Drum, Filter, Reactor, Compressor, Fan, Blower)
3. status_code: 현상코드 (예: 고장, 누설, 작동불량, 소음, 진동, 온도상승, 압력상승, 주기적 점검/정비, 고장.결함.수명소진)
4. priority: 우선순위 (선택사항 - 사용자가 명시적으로 언급한 경우에만 추출)
   - 긴급작업: "긴급", "긴급작업", "최우선", "urgent", "emergency"
   - 우선작업: "우선", "우선작업", "priority", "high priority"
   - 일반작업: "일반", "일반작업", "normal", "regular"
   - 주기작업: "주기", "주기작업", "정기", "PM", "TA"

**추출 규칙**:
1. 문장의 어느 위치에 있든 해당 카테고리의 내용을 찾아 추출
2. 한 단어가 아닌 여러 단어로 구성된 표현도 해당 범주로 인식
3. 유사한 표현이나 동의어도 적절한 카테고리로 매핑
4. 맥락을 고려하여 가장 적절한 카테고리 선택
5. **위치 정보가 가장 중요하므로, 위치 관련 키워드를 우선적으로 찾아 추출**
6. **우선순위는 사용자가 명시적으로 언급한 경우에만 추출하며, 필수 항목이 아님**
7. **한국어-영어 혼용 표현도 정확히 인식** (예: "Pressure Vessel/ Drum" → "Pressure Vessel")
8. **오타, 띄어쓰기, 특수문자 무시하고 의미 파악**

**응답 형식**:
```json
{{
    "location": "추출된 위치/공정",
    "equipment_type": "추출된 설비유형",
    "status_code": "추출된 현상코드",
    "priority": "우선순위",
    "confidence": 0.95,
    "reasoning": "추출 이유"
}}
```

**예시**:
- 입력: "No.1 PE의 Pressure Vessel/ Drum에 고장 발생" → 출력: {{"location": "No.1 PE", "equipment_type": "Pressure Vessel", "status_code": "고장", "priority": null, "confidence": 0.95, "reasoning": "위치와 설비유형, 현상코드 모두 추출"}}
- 입력: "석유제품배합/저장의 Motor Operated Valve, 작동불량. 긴급작업 요망" → 출력: {{"location": "석유제품배합/저장", "equipment_type": "Motor Operated Valve", "status_code": "작동불량", "priority": "긴급작업", "confidence": 0.95, "reasoning": "긴급작업 명시적 언급"}}
- 입력: "합성수지 포장, Miscellaneous Equipment/ Conveyor, 고장, 우선작업 요청" → 출력: {{"location": "합성수지 포장", "equipment_type": "Conveyor", "status_code": "고장", "priority": "우선작업", "confidence": 0.9, "reasoning": "우선작업 명시적 언급"}}
- 입력: "44043-CA1-6"-P, Leak 볼팅 작업" → 출력: {{"location": null, "equipment_type": null, "status_code": "누설", "priority": null, "confidence": 0.8, "reasoning": "ITEMNO 패턴이므로 시나리오 2로 처리"}}

**주의사항**:
- 추출할 수 없는 정보는 null로 설정
- **우선순위는 사용자가 명시적으로 언급한 경우에만 추출하며, 없으면 null로 설정**
- confidence는 0.0~1.0 사이의 값으로 설정
- 대화 히스토리를 참고하여 맥락을 파악
- 여러 단어로 구성된 표현도 정확히 인식
- **한국어-영어 혼용 표현도 정확히 인식하고 정규화**
"""
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """
        LLM 응답을 파싱하여 구조화된 데이터 추출
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            파싱된 데이터 딕셔너리
            
        담당자 수정 가이드:
        - JSON 파싱 실패 시 폴백 로직으로 응답에서 정보 추출
        - 응답 형식이 변경되면 이 메서드 수정 필요
        """
        try:
            # JSON 부분 추출
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # JSON 블록이 없는 경우 전체 텍스트를 JSON으로 파싱 시도
                data = json.loads(response_text)
            
            return data
            
        except Exception as e:
            print(f"LLM 응답 파싱 오류: {e}")
            # 폴백: 간단한 추출 로직으로 응답에서 정보 추출
            return self._extract_from_text_response(response_text)
    
    def _extract_from_text_response(self, response_text: str) -> Dict:
        """
        텍스트 응답에서 정보 추출 (JSON 파싱 실패 시 폴백)
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            추출된 데이터 딕셔너리
        """
        result = {
            'location': None,
            'equipment_type': None,
            'status_code': None,
            'priority': None,
            'confidence': 0.5,
            'reasoning': '텍스트 파싱으로 추출'
        }
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'null' in value.lower():
                    continue
                
                if 'location' in key and value:
                    result['location'] = value
                elif 'equipment_type' in key and value:
                    result['equipment_type'] = value
                elif 'status_code' in key and value:
                    result['status_code'] = value
                elif 'priority' in key and value:
                    result['priority'] = value
                elif 'confidence' in key and value:
                    try:
                        result['confidence'] = float(value)
                    except:
                        pass
        
        return result
    
    def _normalize_extracted_terms(self, parsed_data: Dict) -> Dict:
        """
        추출된 용어를 LLM 정규화 엔진으로 정규화
        
        Args:
            parsed_data: 파싱된 데이터
            
        Returns:
            정규화된 데이터
            
        사용처:
        - _parse_scenario_1()에서 추출된 용어 정규화
        - database.py에서 검색 시 정확한 매칭을 위해 사용
        
        연계 파일:
        - logic/normalizer.py: LLM 정규화 엔진 사용
        
        담당자 수정 가이드:
        - 새로운 카테고리 추가 시 정규화 로직 추가
        - 신뢰도 임계값 조정으로 정규화 품질 제어 가능
        """
        normalized_data = parsed_data.copy()
        
        # 설비유형 정규화
        if parsed_data.get('equipment_type'):
            normalized_term, confidence = normalizer.normalize_term(
                parsed_data['equipment_type'], 'equipment'
            )
            if confidence > 0.3:  # 신뢰도 임계값
                normalized_data['equipment_type'] = normalized_term
        
        # 위치 정규화
        if parsed_data.get('location'):
            normalized_term, confidence = normalizer.normalize_term(
                parsed_data['location'], 'location'
            )
            if confidence > 0.3:
                normalized_data['location'] = normalized_term
        
        # 현상코드 정규화
        if parsed_data.get('status_code'):
            normalized_term, confidence = normalizer.normalize_term(
                parsed_data['status_code'], 'status'
            )
            if confidence > 0.3:
                normalized_data['status_code'] = normalized_term
        
        # 우선순위 정규화
        if parsed_data.get('priority'):
            normalized_term, confidence = normalizer.normalize_term(
                parsed_data['priority'], 'priority'
            )
            if confidence > 0.3:
                normalized_data['priority'] = normalized_term
        
        return normalized_data
    
    def _create_default_parsed_input(self) -> ParsedInput:
        """
        기본 ParsedInput 생성 (오류 시 사용)
        
        Returns:
            기본 ParsedInput 객체
            
        담당자 수정 가이드:
        - 기본값은 비즈니스 로직에 맞게 조정 가능
        - 오류 처리 로직 개선 가능
        """
        return ParsedInput(
            scenario="S1",
            location=None,
            equipment_type=None,
            status_code=None,
            priority=None,
            itemno=None,
            confidence=0.0
        )

    def _create_scenario_1_context_prompt(self, user_input: str, conversation_history: list, accumulated_clues) -> str:
        """
        컨텍스트 포함 시나리오 1 프롬프트 생성
        
        Args:
            user_input: 사용자 입력
            conversation_history: 대화 히스토리
            accumulated_clues: 누적된 단서들
            
        Returns:
            LLM 프롬프트
        """
        prompt = f"""
# 멀티턴 대화 기반 설비관리 입력 분석

## 이전 대화에서 수집된 정보:
- 위치/공정: {accumulated_clues.location or "❌ 미확인"}
- 설비유형: {accumulated_clues.equipment_type or "❌ 미확인"}
- 현상코드: {accumulated_clues.status_code or "❌ 미확인"}
- 우선순위: {accumulated_clues.priority or "⚪ 미지정 (선택사항)"}

## 현재 사용자 입력:
"{user_input}"

## 분석 지시사항:
1. 현재 입력에서 새로운 정보를 추출하세요
2. 이전 정보가 없는 경우에만 새로운 정보를 추출하세요
3. 이전 정보를 수정하려는 의도가 명확한 경우에만 기존 정보를 덮어쓰세요
4. 위치 정보를 최우선으로 추출하세요
5. **설비유형 관련 키워드가 있으면 반드시 추출하세요**
6. **입력 순서와 관계없이 모든 관련 정보를 찾아 추출하세요**

## 추출할 정보:
- location: 위치/공정명 (예: No.1 PE, No.2 PP, 석유제품배합/저장)
- equipment_type: 설비유형 (예: 압력베젤, Pressure Vessel, 펌프, Pump, 열교환기, Heat Exchanger, 탱크, Tank)
- status_code: 현상코드 (예: 고장, 누출, 소음, 진동)
- priority: 우선순위 (선택사항 - 사용자가 명시적으로 언급한 경우에만 추출)
- confidence: 분석 신뢰도 (0.0~1.0)

## 설비유형 키워드 매핑:
- "압력베젤", "베젤", "베셀", "vessel", "pressure vessel" → "Pressure Vessel"
- "펌프", "pump" → "Pump"
- "열교환", "열교환기", "heat exchanger" → "Heat Exchanger"
- "탱크", "tank", "저장탱크" → "Storage Tank"
- "밸브", "valve", "모터밸브" → "Motor Operated Valve"
- "컨베이어", "conveyor" → "Conveyor"
- "필터", "filter" → "Filter"
- "반응기", "reactor" → "Reactor"
- "압축기", "compressor" → "Compressor"
- "팬", "fan" → "Fan"
- "블로워", "blower" → "Blower"

## 응답 형식:
```json
{{
    "location": "추출된 위치 또는 null",
    "equipment_type": "추출된 설비유형 또는 null",
    "status_code": "추출된 현상코드 또는 null",
    "priority": "추출된 우선순위 또는 null",
    "confidence": 0.9
}}
```

## 예시:
사용자 입력: "No.1 PE"
→ location: No.1 PE
→ equipment_type: null
→ status_code: null
→ priority: null
→ confidence: 0.9

사용자 입력: "압력베젤"
→ location: null
→ equipment_type: Pressure Vessel
→ status_code: null
→ priority: null
→ confidence: 0.8

사용자 입력: "고장났어요"
→ location: null
→ equipment_type: null
→ status_code: 고장
→ priority: null
→ confidence: 0.7

사용자 입력: "펌프"
→ location: null
→ equipment_type: Pump
→ status_code: null
→ priority: null
→ confidence: 0.8

사용자 입력: "고장난 펌프" (순서 무관)
→ location: null
→ equipment_type: Pump
→ status_code: 고장
→ priority: null
→ confidence: 0.9
"""
        return prompt

    def _parse_scenario_2(self, user_input: str) -> ParsedInput:
        """
        시나리오 2 파싱: ITEMNO 직접 입력 + 현상 설명 (유사도 기반 매칭)
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            ParsedInput: 파싱된 구조화된 데이터
            
        추출 정보:
        - itemno: 작업대상 (설비 고유번호) - 유사도 기반 매칭
        - status_code: 현상코드 (LLM 추출 + 정규화)
        - priority: 우선순위 (LLM 추출 + 정규화, 기본값: "일반작업")
        """
        try:
            # 1. ITEMNO 추출 (정확한 매칭 → 유사도 매칭)
            itemno = None
            for pattern in self.itemno_patterns:
                match = re.search(pattern, user_input)
                if match:
                    itemno = match.group(0)
                    break
            
            # 2. 정확한 매칭이 없으면 유사도 기반 매칭 시도
            if not itemno:
                itemno = self._find_similar_itemno(user_input)
            
            # 3. 현상코드와 우선순위 LLM 통합 추출 (시나리오1과 동일한 방식)
            status_code, priority = self._extract_status_and_priority_with_llm(user_input)
            
            # 4. 추출된 현상코드 정규화
            normalized_status_code = None
            if status_code:
                normalized_status_code, confidence = normalizer.normalize_term(status_code, 'status')
                # 신뢰도가 낮은 경우 원본 사용
                if confidence < 0.3:
                    normalized_status_code = status_code
            
            # 5. 추출된 우선순위 정규화 (기본값 "일반작업" 적용)
            normalized_priority = "일반작업"  # 기본값
            if priority:
                normalized_priority_term, confidence = normalizer.normalize_term(priority, 'priority')
                # 신뢰도가 충분한 경우 정규화된 값 사용
                if confidence > 0.3:
                    normalized_priority = normalized_priority_term
                else:
                    # 신뢰도가 낮아도 추출된 우선순위가 있으면 사용
                    normalized_priority = priority
            
            # 6. 신뢰도 점수 계산 개선
            confidence = self._calculate_scenario_2_confidence(user_input, itemno, normalized_status_code, normalized_priority)
            
            return ParsedInput(
                scenario="S2",
                location=None,
                equipment_type=None,
                status_code=normalized_status_code,
                priority=normalized_priority,
                itemno=itemno,
                confidence=confidence
            )
            
        except Exception as e:
            print(f"시나리오 2 파싱 오류: {e}")
            return self._create_default_parsed_input()

    def _find_similar_itemno(self, user_input: str) -> Optional[str]:
        """
        사용자 입력에서 ITEMNO와 유사한 패턴을 찾아 DB의 작업대상과 매칭
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            매칭된 ITEMNO 또는 None
        """
        try:
            # DB에서 모든 작업대상 가져오기
            from ..database import DatabaseManager
            db = DatabaseManager()
            
            # 작업대상 컬럼에서 모든 고유값 가져오기
            query = "SELECT DISTINCT itemno FROM notification_history WHERE itemno IS NOT NULL AND itemno != ''"
            cursor = db.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                return None
            
            # 사용자 입력에서 ITEMNO 패턴 추출 시도
            potential_itemno = self._extract_potential_itemno(user_input)
            
            if not potential_itemno:
                return None
            
            # 유사도 계산 및 매칭
            best_match = None
            best_score = 0.0
            min_similarity_threshold = 0.6  # 최소 유사도 임계값
            
            for row in results:
                db_itemno = row[0]
                if db_itemno:
                    # 유사도 계산
                    similarity = self._calculate_similarity(potential_itemno, db_itemno)
                    
                    if similarity > best_score and similarity >= min_similarity_threshold:
                        best_score = similarity
                        best_match = db_itemno
            
            return best_match
            
        except Exception as e:
            print(f"유사도 매칭 오류: {e}")
            return None
    
    def _extract_potential_itemno(self, user_input: str) -> Optional[str]:
        """
        사용자 입력에서 잠재적인 ITEMNO 패턴 추출 (개선됨)
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            추출된 패턴 또는 None
        """
        # 다양한 ITEMNO 패턴 시도 (따옴표 포함 패턴 추가)
        patterns = [
            r'\b\d{4,}-[A-Z]{1,4}\d*-\d+"-[A-Z]\b',  # 44043-CA1-6"-P (따옴표 포함)
            r'\b\d{4,}-[A-Z]{1,4}\d*-\d+-[A-Z]\b',   # 44043-CA1-6-P (일반)
            r'\b\d{4,}-\w+',                          # 44043-CA1
            r'\b[A-Z]-\w+\d+',                        # Y-MV1035  
            r'\b[A-Z]{2,4}-\w+-\d{2}\b',              # SW-CV1307-02
            r'\b[A-Z]{2,4}-\w+',                      # PE-SE1304B
            r'\b\d{5,}',                              # 5자리 이상 숫자
            r'\b[A-Z]{2,4}\d+',                       # PE12345
            r'"[^"]*"',                               # 따옴표로 둘러싸인 모든 패턴
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                extracted = match.group(0)
                # 따옴표로 둘러싸인 경우 따옴표 제거
                if extracted.startswith('"') and extracted.endswith('"'):
                    extracted = extracted[1:-1]
                return extracted
        
        return None
    
    def _calculate_similarity(self, input_itemno: str, db_itemno: str) -> float:
        """
        두 ITEMNO 간의 유사도 계산 (개선됨)
        
        Args:
            input_itemno: 사용자 입력 ITEMNO
            db_itemno: DB의 ITEMNO
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        # 특수문자 정규화 (따옴표, 공백 등 제거)
        normalized_input = self._normalize_itemno_for_comparison(input_itemno)
        normalized_db = self._normalize_itemno_for_comparison(db_itemno)
        
        # 1. 정규화된 정확한 매칭
        if normalized_input == normalized_db:
            return 1.0
        
        # 2. 기본 문자열 유사도 (정규화된 문자열로)
        base_similarity = SequenceMatcher(None, normalized_input, normalized_db).ratio()
        
        # 3. 추가 규칙들
        bonus = 0.0
        
        # 부분 매칭 (포함 관계)
        if normalized_input in normalized_db or normalized_db in normalized_input:
            bonus += 0.2
        
        # 숫자 부분 매칭 (핵심 부분)
        input_numbers = re.findall(r'\d+', normalized_input)
        db_numbers = re.findall(r'\d+', normalized_db)
        if input_numbers and db_numbers:
            number_matches = sum(1 for in_num in input_numbers 
                               for db_num in db_numbers 
                               if in_num == db_num or in_num in db_num or db_num in in_num)
            if number_matches > 0:
                bonus += 0.3 * (number_matches / max(len(input_numbers), len(db_numbers)))
        
        # 문자 부분 매칭
        input_letters = re.findall(r'[A-Za-z]+', normalized_input)
        db_letters = re.findall(r'[A-Za-z]+', normalized_db)
        if input_letters and db_letters:
            letter_matches = sum(1 for in_letter in input_letters 
                               for db_letter in db_letters 
                               if in_letter.lower() == db_letter.lower())
            if letter_matches > 0:
                bonus += 0.2 * (letter_matches / max(len(input_letters), len(db_letters)))
        
        # 패턴 구조 유사성 (하이픈 위치 등)
        input_pattern = re.sub(r'[A-Za-z]+', 'L', re.sub(r'\d+', 'N', normalized_input))
        db_pattern = re.sub(r'[A-Za-z]+', 'L', re.sub(r'\d+', 'N', normalized_db))
        if input_pattern == db_pattern:
            bonus += 0.1
        
        return min(1.0, base_similarity + bonus)
    
    def _normalize_itemno_for_comparison(self, itemno: str) -> str:
        """
        ITEMNO를 비교용으로 정규화 (특수문자 제거)
        
        Args:
            itemno: 원본 ITEMNO
            
        Returns:
            정규화된 ITEMNO
        """
        if not itemno:
            return ""
        
        # 1. 소문자 변환
        normalized = itemno.lower()
        
        # 2. 따옴표 제거 (인치 표시 등)
        normalized = re.sub(r'["\'`]', '', normalized)
        
        # 3. 연속된 공백을 하나로 통합
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 4. 앞뒤 공백 제거
        normalized = normalized.strip()
        
        return normalized
    
    def _is_exact_match(self, user_input: str, itemno: str) -> bool:
        """
        사용자 입력에서 정확한 ITEMNO 매칭 여부 확인
        
        Args:
            user_input: 사용자 입력 메시지
            itemno: 매칭된 ITEMNO
            
        Returns:
            정확한 매칭 여부
        """
        # 정규표현식 패턴으로 정확한 매칭 확인
        for pattern in self.itemno_patterns:
            match = re.search(pattern, user_input)
            if match and match.group(0) == itemno:
                return True
        
        return False

    def _extract_status_and_priority_with_llm(self, user_input: str) -> Tuple[Optional[str], Optional[str]]:
        """
        시나리오 2용 LLM 기반 현상코드와 우선순위 통합 추출
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            (추출된 현상코드, 추출된 우선순위) 튜플
        """
        try:
            # LLM 프롬프트 생성
            prompt = f"""
다음 사용자 입력에서 설비 현상코드와 우선순위를 추출해주세요.

**사용자 입력**: {user_input}

**추출 대상**:
1. 현상코드: 설비의 상태나 문제점을 나타내는 표현
   - 예시: 고장, 누설, 작동불량, 소음, 진동, 온도상승, 압력상승, 점검, 정비, 결함, 수명소진, leak, bolting 등

2. 우선순위: 작업의 긴급도를 나타내는 표현 (선택사항)
   - 긴급작업: "긴급", "긴급작업", "최우선", "urgent", "emergency", "즉시", "바로"
   - 우선작업: "우선", "우선작업", "priority", "high priority", "먼저", "중요"
   - 일반작업: "일반", "일반작업", "normal", "regular", "보통"
   - 주기작업: "주기", "주기작업", "정기", "PM", "TA", "점검"

**추출 규칙**:
1. 현상코드: 설비 상태나 문제점을 직접적으로 표현하는 단어나 구문 추출
2. 우선순위: 사용자가 명시적으로 언급한 경우에만 추출
3. 여러 현상이 언급된 경우 가장 주요한 현상 하나만 추출
4. 현상/우선순위와 관련 없는 단어는 제외 (ITEMNO, 위치, 작업 등)
5. 해당 정보가 없는 경우 "None" 반환

**응답 형식**:
```json
{{
    "status_code": "추출된 현상코드 또는 None",
    "priority": "추출된 우선순위 또는 None"
}}
```

**예시**:
- 입력: "44043-CA1-6"-P, Leak 볼팅 작업" → 출력: {{"status_code": "leak", "priority": "None"}}
- 입력: "Y-MV1035. 고장" → 출력: {{"status_code": "고장", "priority": "None"}}
- 입력: "SW-CV1307-02, 소음 발생, 우선작업" → 출력: {{"status_code": "소음", "priority": "우선작업"}}
- 입력: "44043-CA1-6"-P, 결함, 긴급작업" → 출력: {{"status_code": "결함", "priority": "긴급작업"}}
- 입력: "PE-SE1304B" → 출력: {{"status_code": "None", "priority": "None"}}
"""
            
            # LLM 호출
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 설비관리 시스템의 현상코드와 우선순위 추출 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150
            )
            
            result = response.choices[0].message.content.strip()
            
            # 응답 파싱
            parsed_result = self._parse_status_priority_response(result)
            
            status_code = parsed_result.get("status_code")
            priority = parsed_result.get("priority")
            
            # "None" 문자열을 실제 None으로 변환
            if status_code == "None":
                status_code = None
            if priority == "None":
                priority = None
            
            return status_code, priority
            
        except Exception as e:
            print(f"LLM 현상코드/우선순위 추출 오류: {e}")
            # 폴백: 기존 방식으로 처리
            return self._extract_status_and_priority_fallback(user_input)
    
    def _parse_status_priority_response(self, response_text: str) -> Dict:
        """
        현상코드/우선순위 추출 응답 파싱
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            파싱된 딕셔너리
        """
        try:
            # JSON 부분 추출
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # JSON 블록이 없는 경우 전체 텍스트를 JSON으로 파싱 시도
                data = json.loads(response_text)
            
            return data
            
        except Exception as e:
            print(f"현상코드/우선순위 응답 파싱 오류: {e}")
            return {"status_code": "None", "priority": "None"}
    
    def _extract_status_and_priority_fallback(self, user_input: str) -> Tuple[Optional[str], Optional[str]]:
        """
        LLM 실패 시 폴백용 현상코드/우선순위 추출
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            (추출된 현상코드, 추출된 우선순위) 튜플
        """
        # 현상코드 추출
        status_keywords = [
            '고장', '누설', '작동불량', '소음', '진동', '온도상승', '압력상승', 
            '점검', '정비', '결함', '수명소진', 'leak', 'bolting'
        ]
        
        status_code = None
        for keyword in status_keywords:
            if keyword.lower() in user_input.lower():
                status_code = keyword
                break
        
        # 우선순위 추출
        priority = None
        for priority_type, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword.lower() in user_input.lower():
                    priority = priority_type
                    break
            if priority:
                break
        
        return status_code, priority

    def _extract_status_code_with_llm(self, user_input: str) -> Optional[str]:
        """
        시나리오 2용 LLM 기반 현상코드 추출 (기존 메서드 유지 - 호환성)
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            추출된 현상코드 또는 None
        """
        # 통합 메서드 호출
        status_code, _ = self._extract_status_and_priority_with_llm(user_input)
        return status_code

    def _calculate_scenario_2_confidence(self, user_input: str, itemno: str, status_code: str, priority: str) -> float:
        """
        시나리오 2용 신뢰도 점수 계산
        
        Args:
            user_input: 사용자 입력
            itemno: 추출된 ITEMNO
            status_code: 추출된 현상코드
            priority: 추출된 우선순위
            
        Returns:
            신뢰도 점수 (0.0 ~ 1.0)
        """
        confidence = 0.0
        
        # ITEMNO 존재 여부 (기본 점수)
        if itemno:
            if self._is_exact_match(user_input, itemno):
                confidence += 0.5  # 정확한 매칭
            else:
                confidence += 0.3  # 유사도 매칭
        
        # 현상코드 존재 여부
        if status_code:
            confidence += 0.3
        
        # 우선순위 존재 여부 (보너스)
        if priority:
            confidence += 0.1
        
        # 입력 복잡도 고려
        if ',' in user_input:  # 여러 정보가 포함된 경우
            confidence += 0.1
        
        return min(1.0, confidence)

    def _parse_default_scenario(self, user_input: str) -> ParsedInput:
        """
        기본 시나리오 파싱
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            ParsedInput: 기본 파싱 결과
        """
        return ParsedInput(
            scenario="default",
            location=None,
            equipment_type=None,
            status_code=None,
            priority=None,
            itemno=None,
            confidence=0.3
        )

# 전역 입력 파서 인스턴스
# 다른 모듈에서 import하여 사용
input_parser = InputParser() 