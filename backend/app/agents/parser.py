"""
PMark1 AI Assistant - 자연어 입력 파서

이 파일은 사용자의 자연어 입력을 분석하여 구조화된 데이터로 변환합니다.
OpenAI GPT-4o를 활용하여 시나리오를 판단하고, 관련 정보를 추출합니다.

주요 담당자: AI/ML 엔지니어, 백엔드 개발자
수정 시 주의사항:
- OpenAI API 키가 필요합니다 (config.py에서 설정)
- 시나리오 판단 로직은 비즈니스 요구사항에 따라 조정
- 추출 필드는 models.py의 ParsedInput과 일치해야 함
"""

import re
from openai import OpenAI
from typing import Dict, List, Optional, Tuple
from ..config import Config
from ..models import ParsedInput
from ..logic.normalizer import normalizer
import json

class InputParser:
    """
    자연어 입력 파서 클래스
    
    사용처:
    - chat.py: POST /api/v1/chat에서 사용자 입력 분석
    - recommender.py: RecommendationEngine에서 파싱 결과 활용
    
    연계 파일:
    - models.py: ParsedInput 모델 사용
    - config.py: OpenAI API 설정
    - logic/normalizer.py: 추출된 용어 정규화
    
    담당자 수정 가이드:
    - 새로운 시나리오 추가 시 _create_scenario_prompt() 메서드 수정
    - 추출 필드 변경 시 models.py의 ParsedInput도 함께 수정
    - 프롬프트 수정 시 일관성 있는 응답을 위해 temperature 조정
    """
    
    def __init__(self):
        """
        입력 파서 초기화
        
        설정:
        - OpenAI 클라이언트 초기화
        - 모델 설정
        - 세션 기반 누적 정보 저장소
        """
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # 세션별 누적 정보 저장소
        self.session_accumulated_info = {}
        
        # ITEMNO 패턴 (채번 규칙)
        self.itemno_patterns = [
            r'\b[A-Z]{2,4}-\d{5}\b',  # 예: RFCC-00123
            r'\b[A-Z]-\w+\b',         # 예: Y-MV1035
            r'\b\d{5}-[A-Z]{2}-\d+"-[A-Z]\b',  # 예: 44043-CA1-6"-P
            r'\b[A-Z]{2}-\w+-\d{2}\b',  # 예: SW-CV1307-02
        ]
        
        # 우선순위 키워드
        self.priority_keywords = {
            "긴급작업": ["긴급", "긴급작업", "urgent", "emergency"],
            "우선작업": ["우선", "우선작업", "priority", "high"],
            "일반작업": ["일반", "일반작업", "normal", "regular"]
        }
    
    def parse_input(self, user_input: str, conversation_history: list = None, session_id: str = None) -> ParsedInput:
        """
        사용자 입력을 파싱하여 구조화된 데이터로 변환
        
        Args:
            user_input: 사용자 입력 메시지
            conversation_history: 대화 히스토리 (멀티턴 처리용)
            session_id: 세션 ID (누적 정보 관리용)
            
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
        
        # 세션 기반 파싱 시도 (session_id가 있는 경우)
        if session_id:
            try:
                return self.parse_input_with_context(user_input, conversation_history, session_id)
            except Exception as e:
                print(f"세션 기반 파싱 실패, 기본 파싱으로 전환: {e}")
                # 기본 파싱으로 fallback
        
        try:
            # 시나리오 판단
            scenario = self._determine_scenario(user_input)
            
            if scenario == "S1":
                # 시나리오 1: 자연어로 작업 요청
                return self._parse_scenario_1(user_input, conversation_history, session_id)
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
                priority="일반작업",
                itemno=None,
                confidence=0.0
            )
    
    def parse_input_with_context(self, user_input: str, conversation_history: list = None, session_id: str = None) -> ParsedInput:
        """
        세션 컨텍스트를 포함한 입력 파싱 (PMark2.5 고급 기능)
        
        Args:
            user_input: 사용자 입력 메시지
            conversation_history: 대화 히스토리
            session_id: 세션 ID
            
        Returns:
            ParsedInput: 컨텍스트를 반영한 파싱 결과
        """
        try:
            # 세션 컨텍스트 로드
            from .session_manager import session_manager
            session_state = session_manager.get_session(session_id) if session_id else None
            
            if session_state:
                # 기존 누적 단서와 함께 파싱
                return self._parse_scenario_1_with_context(user_input, conversation_history, session_state.accumulated_clues)
            else:
                # 일반 파싱
                return self.parse_input(user_input, conversation_history)
                
        except Exception as e:
            print(f"컨텍스트 파싱 오류: {e}")
            # 기본 파싱으로 fallback
            return self.parse_input(user_input, conversation_history)

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
                model="gpt-4o",
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
            
            # 누락된 필드 확인
            missing_fields = []
            if not normalized_data.get("location") and not accumulated_clues.location:
                missing_fields.append("location")
            if not normalized_data.get("equipment_type") and not accumulated_clues.equipment_type:
                missing_fields.append("equipment_type")
            if not normalized_data.get("status_code") and not accumulated_clues.status_code:
                missing_fields.append("status_code")
            
            # ParsedInput 객체 생성
            parsed_input = ParsedInput(
                scenario="S1",
                location=normalized_data.get("location"),
                equipment_type=normalized_data.get("equipment_type"),
                status_code=normalized_data.get("status_code"),
                priority=normalized_data.get("priority") or "일반작업",
                itemno=normalized_data.get("itemno"),
                confidence=normalized_data.get("confidence", 0.8),
                missing_items=missing_fields,
                needs_additional_input=len(missing_fields) > 0
            )
            
            print(f"컨텍스트 파싱 완료: {parsed_input}")
            return parsed_input
            
        except Exception as e:
            print(f"컨텍스트 파싱 오류: {e}")
            import traceback
            traceback.print_exc()
            # 기본 파싱으로 fallback
            return self._parse_scenario_1(user_input, conversation_history)

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
- 위치: {accumulated_clues.location or "❌ 미확인"}
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
- location: 위치 (예: No.1 PE, No.2 PE, 석유제품배합/저장)
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
    "confidence": 0.8,
    "reasoning": "분석 과정 설명"
}}
```

## 예시:
사용자 입력: "No.1 PE"
→ location: "No.1 PE", equipment_type: null, status_code: null, priority: null, confidence: 0.9

사용자 입력: "압력베젤"
→ location: null, equipment_type: "Pressure Vessel", status_code: null, priority: null, confidence: 0.8

사용자 입력: "고장났어요"
→ location: null, equipment_type: null, status_code: "고장", priority: null, confidence: 0.7

사용자 입력: "펌프"
→ location: null, equipment_type: "Pump", status_code: null, priority: null, confidence: 0.8

사용자 입력: "고장난 펌프" (순서 무관)
→ location: null, equipment_type: "Pump", status_code: "고장", priority: null, confidence: 0.9
"""
        return prompt
    
    def clear_session(self, session_id: str):
        """
        세션 종료 시 누적 정보 삭제
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.session_accumulated_info:
            del self.session_accumulated_info[session_id]
    
    def _determine_scenario(self, user_input: str) -> str:
        """
        사용자 입력을 분석하여 시나리오 판단
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            시나리오 타입 ("S1", "S2", "default")
            
        판단 기준:
        - S1: 자연어로 작업 요청 (위치, 설비, 현상 등 포함)
        - S2: ITEMNO로 작업 상세 요청 (DB 작업대상 컬럼에 존재)
        - default: 기타
        
        담당자 수정 가이드:
        - 시나리오 판단 기준은 비즈니스 요구사항에 따라 조정
        - DB 조회 기반으로 정확한 ITEMNO 매칭 수행
        """
        # 1단계: DB 작업대상 컬럼에서 직접 확인 (가장 정확한 방법)
        if self._check_itemno_in_db(user_input):
            return "S2"
        
        # 2단계: 기존 ITEMNO 패턴 확인 (백업 로직)
        if re.search(r'ITEMNO\s*\d+', user_input, re.IGNORECASE):
            return "S2"
            
        # 3단계: 일반적인 ITEMNO 패턴 확인 (백업 로직)
        itemno_patterns = [
            r'\b[A-Z]{2,4}-[A-Z0-9]+\b',  # PE-V2884, NX-RGV305 등
            r'\b[A-Z]{2,4}-[A-Z]+\d+[A-Z]*\b',  # PW-AI376AB 등
            r'\b\d{5,}-[A-Z0-9-]+\b',  # 숫자로 시작하는 복합 패턴
            r'"[^"]*"',  # 따옴표로 둘러싸인 코드
        ]
        
        for pattern in itemno_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return "S2"
        
        # 4단계: 자연어 작업 요청으로 분류 (기본값)
        return "S1"
    
    def _check_itemno_in_db(self, user_input: str) -> bool:
        """
        사용자 입력이 DB의 작업대상 컬럼에 존재하는지 확인
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            bool: 작업대상 컬럼에 존재하면 True, 없으면 False
        """
        try:
            from ..database import DatabaseManager
            db = DatabaseManager()
            
            # 입력에서 잠재적인 ITEMNO 패턴들 추출
            potential_items = self._extract_potential_itemno_patterns(user_input)
            
            if not potential_items:
                return False
            
            # DB에서 작업대상 컬럼 조회
            query = "SELECT DISTINCT itemno FROM notification_history WHERE itemno IS NOT NULL AND itemno != ''"
            cursor = db.conn.execute(query)
            db_items = [row[0] for row in cursor.fetchall()]
            
            # 정확한 매칭 확인
            for item in potential_items:
                if item in db_items:
                    return True
            
            # 유사도 기반 매칭 (높은 유사도만)
            for item in potential_items:
                for db_item in db_items:
                    if self._calculate_itemno_similarity(item, db_item) > 0.8:
                        return True
            
            return False
            
        except Exception as e:
            print(f"DB 조회 오류: {e}")
            return False
    
    def _extract_potential_itemno_patterns(self, user_input: str) -> list:
        """
        사용자 입력에서 잠재적인 ITEMNO 패턴들을 추출
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            list: 추출된 패턴들
        """
        patterns = []
        
        # 다양한 ITEMNO 패턴 매칭
        itemno_regex_patterns = [
            r'\b[A-Z]{2,4}-[A-Z0-9]+\b',  # PE-V2884, NX-RGV305
            r'\b[A-Z]{2,4}-[A-Z]+\d+[A-Z]*\b',  # PW-AI376AB
            r'\b\d{5,}-[A-Z0-9-]+\b',  # 숫자로 시작하는 패턴
            r'"([^"]*)"',  # 따옴표로 둘러싸인 내용
            r'\b[A-Z]{2,4}\d+[A-Z]*\b',  # 문자+숫자 조합
        ]
        
        for pattern in itemno_regex_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            patterns.extend(matches)
        
        # 중복 제거 및 정리
        return list(set([p.strip() for p in patterns if p.strip()]))
    
    def _calculate_itemno_similarity(self, item1: str, item2: str) -> float:
        """
        두 ITEMNO 간의 유사도 계산
        
        Args:
            item1: 첫 번째 ITEMNO
            item2: 두 번째 ITEMNO
            
        Returns:
            float: 유사도 점수 (0.0 ~ 1.0)
        """
        from difflib import SequenceMatcher
        
        # 기본 문자열 유사도
        similarity = SequenceMatcher(None, item1.lower(), item2.lower()).ratio()
        
        # 정확한 매칭 보너스
        if item1.lower() == item2.lower():
            return 1.0
        
        # 부분 매칭 보너스
        if item1.lower() in item2.lower() or item2.lower() in item1.lower():
            similarity += 0.2
        
        return min(1.0, similarity)
    
    def _parse_scenario_1(self, user_input: str, conversation_history: list = None, session_id: str = None) -> ParsedInput:
        """
        시나리오 1 파싱: 자연어로 작업 요청
        
        Args:
            user_input: 사용자 입력 메시지
            conversation_history: 대화 히스토리 (멀티턴 처리용)
            session_id: 세션 ID (누적 정보 관리용)
            
        Returns:
            ParsedInput: 파싱된 구조화된 데이터
            
        추출 정보:
        - location: 위치/공정
        - equipment_type: 설비유형
        - status_code: 현상코드
        - priority: 우선순위
        
        담당자 수정 가이드:
        - LLM 프롬프트 수정으로 추출 정확도 개선 가능
        - 정규화 로직 개선으로 DB 매칭 정확도 향상
        - 대화 히스토리 활용 로직 개선으로 멀티턴 처리 향상
        """
        try:
            # 세션별 누적 정보 가져오기
            accumulated_info = self.session_accumulated_info.get(session_id, {})
            
            # LLM 프롬프트 생성
            prompt = self._create_scenario_1_prompt(user_input, conversation_history, accumulated_info)
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            
            # 응답 파싱
            parsed_data = self._parse_llm_response(result_text)
            
            # 추출된 용어 정규화
            normalized_data = self._normalize_extracted_terms(parsed_data)
            
            # S1_2-1: 단서 항목 포함 여부 파악
            # S1_2-2: 조건 충족 여부 (주요 3개 단서 항목: location, equipment_type, status_code)
            main_clues = ['location', 'equipment_type', 'status_code']
            present_clues = [clue for clue in main_clues if normalized_data.get(clue)]
            missing_clues = [clue for clue in main_clues if not normalized_data.get(clue)]
            
            # 누적된 정보와 현재 정보 결합
            combined_data = self._combine_accumulated_info(normalized_data, accumulated_info)
            
            # 세션별 누적 정보 업데이트
            if session_id:
                self.session_accumulated_info[session_id] = combined_data.copy()
            
            # S1_2-2: 조건 충족 여부 판단 (주요 3개 단서 항목 모두 있는지 확인)
            main_clues_final = ['location', 'equipment_type', 'status_code']
            present_clues_final = [clue for clue in main_clues_final if combined_data.get(clue)]
            missing_clues_final = [clue for clue in main_clues_final if not combined_data.get(clue)]
            
            # 조건 충족 여부에 따른 분기
            if len(present_clues_final) == 3:
                # S1_2-3: 스키마 매핑 - 3개 단서 항목 모두 있을 때
                needs_additional_input = False
                confidence = parsed_data.get('confidence', 0.8)
            else:
                # S1_2-4: 추가 입력 요청 - 3개 단서 항목 중 누락된 것이 있을 때
                needs_additional_input = True
                confidence = parsed_data.get('confidence', 0.5)
            
            # 우선순위 기본값 처리
            priority = combined_data.get('priority')
            if not priority:
                priority = "일반작업"
            
            return ParsedInput(
                scenario="S1",
                location=combined_data.get('location'),
                equipment_type=combined_data.get('equipment_type'),
                status_code=combined_data.get('status_code'),
                priority=priority,
                itemno=None,
                confidence=confidence,
                missing_items=missing_clues_final,  # 누락된 주요 단서 항목 목록
                needs_additional_input=needs_additional_input  # 추가 입력 필요 여부
            )
            
        except Exception as e:
            print(f"시나리오 1 파싱 오류: {e}")
            return self._create_default_parsed_input()
    
    def _check_missing_items(self, normalized_data: Dict) -> List[str]:
        """
        주요 3개 단서 항목 중 누락된 항목 확인 (S1_2-2)
        
        Args:
            normalized_data: 정규화된 데이터
            
        Returns:
            누락된 항목 목록
        """
        missing_items = []
        
        # 주요 3개 단서 항목 확인
        if not normalized_data.get('location'):
            missing_items.append('location')
        if not normalized_data.get('equipment_type'):
            missing_items.append('equipment_type')
        if not normalized_data.get('status_code'):
            missing_items.append('status_code')
        
        return missing_items
    
    def _parse_scenario_2(self, user_input: str) -> ParsedInput:
        """
        시나리오 2 파싱: ITEMNO로 작업 상세 요청
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            ParsedInput: 파싱된 구조화된 데이터
            
        추출 정보:
        - itemno: 작업대상 (설비 코드)
        - status_code: 현상코드 (설비 상황/정비수요 묘사)
        - priority: 우선순위 (선택사항)
        
        담당자 수정 가이드:
        - S2_2-1: 작업대상과 현상코드 2개 단서 항목 확인
        - S2_2-2: 조건 충족 여부 판단 (2개 모두 있는지)
        - S2_2-3: 스키마 매핑 수행
        """
        try:
            # S2_2-1: 단서 항목 포함 여부 파악
            # 1) 작업대상(ITEMNO) 추출
            itemno = self._extract_itemno_from_input(user_input)
            
            # 2) 현상코드 추출 (설비 상황/정비수요 묘사)
            status_code = self._extract_status_from_input(user_input)
            
            # 3) 우선순위 추출 (선택사항)
            priority = self._extract_priority_from_input(user_input)
            
            # S2_2-2: 조건 충족 여부 판단 (작업대상 + 현상코드 2개 모두 있는지)
            main_clues_s2 = [itemno, status_code]
            present_clues_s2 = [clue for clue in main_clues_s2 if clue]
            missing_clues_s2 = []
            
            if not itemno:
                missing_clues_s2.append('itemno')
            if not status_code:
                missing_clues_s2.append('status_code')
            
            # 조건 충족 여부에 따른 분기
            if len(present_clues_s2) == 2:
                # S2_2-3: 스키마 매핑 - 2개 단서 항목 모두 있을 때
                needs_additional_input = False
                confidence = 0.8
            else:
                # S2_2-4: 추가 입력 요청 - 2개 단서 항목 중 누락된 것이 있을 때
                needs_additional_input = True
                confidence = 0.5
            
            # 우선순위 기본값 처리
            if not priority:
                priority = "일반작업"
            
            return ParsedInput(
                scenario="S2",
                location=None,
                equipment_type=None,
                status_code=status_code,
                priority=priority,
                itemno=itemno,
                confidence=confidence,
                missing_items=missing_clues_s2,  # 누락된 단서 항목 목록
                needs_additional_input=needs_additional_input  # 추가 입력 필요 여부
            )
            
        except Exception as e:
            print(f"시나리오 2 파싱 오류: {e}")
            return self._create_default_parsed_input()
    
    def _extract_itemno_from_input(self, user_input: str) -> str:
        """
        사용자 입력에서 작업대상(ITEMNO) 추출
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            추출된 ITEMNO 또는 None
        """
        # 기존 패턴 매칭 활용
        potential_items = self._extract_potential_itemno_patterns(user_input)
        
        if potential_items:
            # 첫 번째 매칭된 항목 반환
            return potential_items[0]
        
        return None
    
    def _extract_status_from_input(self, user_input: str) -> str:
        """
        사용자 입력에서 현상코드(설비 상황/정비수요 묘사) 추출
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            추출된 현상코드 또는 None
        """
        # 현상코드 관련 키워드 매칭
        status_keywords = [
            '고장', '누설', '작동불량', '소음', '진동', '온도상승', '압력상승',
            '점검', '정비', '결함', '수명소진', '고장.결함.수명소진',
            '주기적 점검/정비', 'SHE', '운전 Condition 이상', '기타',
            '예방 점검/정비', '법규', '정기/임시 보수', '설비개선', '예지정비',
            'leak', 'bolting', 'failure', 'maintenance', 'inspection'
        ]
        
        user_input_lower = user_input.lower()
        
        # 키워드 매칭
        for keyword in status_keywords:
            if keyword.lower() in user_input_lower:
                return keyword
        
        return None
    
    def _extract_priority_from_input(self, user_input: str) -> str:
        """
        사용자 입력에서 우선순위 추출
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            추출된 우선순위 또는 None
        """
        priority_keywords = {
            "긴급작업": ["긴급", "긴급작업", "최우선", "urgent", "emergency", "긴급하게", "즉시", "바로"],
            "우선작업": ["우선", "우선작업", "priority", "high", "우선적으로", "먼저", "중요"],
            "일반작업": ["일반", "일반작업", "normal", "regular", "보통", "평상시", "정상"],
            "주기작업": ["주기", "주기작업", "TA", "PM", "정기", "정기적", "주기적", "점검"]
        }
        
        user_input_lower = user_input.lower()
        
        for priority_type, keywords in priority_keywords.items():
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    return priority_type
        
        return None
    
    def _parse_default_scenario(self, user_input: str) -> ParsedInput:
        """
        기본 시나리오 파싱
        
        Args:
            user_input: 사용자 입력 메시지
            
        Returns:
            ParsedInput: 기본 파싱 결과
            
        담당자 수정 가이드:
        - 기본 시나리오 처리 로직 개선 가능
        - 사용자 안내 메시지 생성 로직 추가 가능
        """
        return ParsedInput(
            scenario="S1",
            location=None,
            equipment_type=None,
            status_code=None,
            priority="일반작업",
            itemno=None,
            confidence=0.0
        )
    
    def _create_scenario_1_prompt(self, user_input: str, conversation_history: list = None, accumulated_info: Dict = None) -> str:
        """
        시나리오 1용 LLM 프롬프트 생성
        
        Args:
            user_input: 사용자 입력 메시지
            conversation_history: 대화 히스토리 (멀티턴 처리용)
            accumulated_info: 이전 대화에서 누적된 정보
            
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
        
        # 누적된 정보 추가
        accumulated_context = ""
        if accumulated_info:
            accumulated_context = "세션에서 누적된 정보:\n"
            for key, value in accumulated_info.items():
                if value:
                    accumulated_context += f"{key}: {value}\n"
            accumulated_context += "\n"
        
        return f"""
{context}{accumulated_context}다음 사용자 입력을 분석하여 설비관리 작업 요청 관련 정보를 4개 범주로 분류하여 추출해주세요.

**사용자 입력**: {user_input}

**핵심 원칙**:
1. **LLM 언어 능력 활용**: 완전한 문장이 아닌 단어나 불완전한 입력도 언어 능력을 사용하여 4개 범주로 분류
2. **범주별 파싱**: 입력된 모든 내용을 위치, 설비유형, 현상코드, 우선순위 중 하나의 범주로 분류
3. **누적 정보 활용**: 세션에서 누적된 정보와 현재 입력을 결합하여 완전한 정보 구성
4. **의미 기반 인식**: 한국어-영어 혼용, 오타, 띄어쓰기 오류를 무시하고 의미 파악

**추출해야 할 4개 범주**:
1. **location**: 위치 (예: No.1 PE, No.2 PE, 석유제품배합/저장, 합성수지 포장, RFCC, 1창고 #7Line, 2창고 #8Line, 공통 시설)
2. **equipment_type**: 설비유형 (예: Pressure Vessel, Motor Operated Valve, Conveyor, Pump, Heat Exchanger, Valve, Control Valve, Tank, Storage Tank, Drum, Filter, Reactor, Compressor, Fan, Blower)
3. **status_code**: 현상코드 (예: 고장, 누설, 작동불량, 소음, 진동, 온도상승, 압력상승, 주기적 점검/정비, 고장.결함.수명소진)
4. **priority**: 우선순위 (예: 긴급작업(최우선순위), 우선작업(Deadline준수), 일반작업(Deadline없음), 주기작업(TA.PM))

**범주별 파싱 규칙**:
1. **다중 단어 인식**: 각 범주는 한 단어가 아닌 여러 단어로 구성될 수 있음
   - 위치: "1창고 7번 라인", "석유제품배합/저장", "No.1 PE 공정" 등
   - 설비유형: "Motor Operated Valve", "Pressure Vessel/ Drum" 등
   - 현상코드: "고장.결함.수명소진", "주기적 점검/정비" 등
   - 우선순위: "긴급작업(최우선순위)", "우선작업(Deadline준수)" 등

2. **복합 표현 처리**: 동일한 개념의 여러 표현이 하나의 범주에 속할 수 있음
   - 예: "1창고", "7번 라인" → 모두 위치 범주로 통합하여 "1창고 7번 라인"
   - 예: "압력", "베젤" → 모두 설비유형 범주로 통합하여 "Pressure Vessel"

3. **맥락 기반 추론**: 불완전한 입력도 맥락을 고려하여 가장 적절한 범주로 분류
4. **의미 기반 매핑**: 유사한 표현이나 동의어도 적절한 범주로 매핑
5. **누적 정보 결합**: 세션에서 누적된 정보가 있으면 현재 입력과 결합
6. **기본값 처리**: 우선순위가 명시되지 않으면 "일반작업"으로 설정

**한국어-영어 혼용 인식 규칙**:
- 한국어와 영어가 혼용된 표현도 정확히 인식 (예: "압력베젤" ↔ "Pressure Vessel")
- 오타, 띄어쓰기 오류, 특수문자를 무시하고 의미 파악
- 복합 표현의 각 부분을 종합하여 완전한 의미 파악 (예: "1창고 #7Line" → "1창고 7번 라인")
- 유사한 의미의 표현들을 동일한 범주로 매핑
- 문맥을 고려하여 가장 적절한 표준 용어로 변환

**응답 형식**:
```json
{{
    "location": "추출된 위치/공정",
    "equipment_type": "추출된 설비유형",
    "status_code": "추출된 현상코드",
    "priority": "우선순위",
    "confidence": 0.95,
    "reasoning": "범주별 분류 이유"
}}
```

**예시**:
- 입력: "No.1 PE의 Pressure Vessel/ Drum에 고장 발생" → 출력: {{"location": "No.1 PE", "equipment_type": "Pressure Vessel/ Drum", "status_code": "고장", "priority": "일반작업", "confidence": 0.95, "reasoning": "완전한 문장에서 4개 범주 모두 추출"}}
- 입력: "모터밸브" → 출력: {{"location": null, "equipment_type": "Motor Operated Valve", "status_code": null, "priority": "일반작업", "confidence": 0.9, "reasoning": "단일 단어를 설비유형으로 분류"}}
- 입력: "누설" → 출력: {{"location": null, "equipment_type": null, "status_code": "누설", "priority": "일반작업", "confidence": 0.9, "reasoning": "단일 단어를 현상코드로 분류"}}
- 입력: "긴급하게 2창고 컨베이어가 작동하지 않아요" → 출력: {{"location": "2창고 #8Line", "equipment_type": "Conveyor", "status_code": "작동불량", "priority": "긴급작업(최우선순위)", "confidence": 0.95, "reasoning": "긴급 키워드와 작동불량 상황을 종합 분석"}}
- 입력: "석유제품 저장탱크에서 소음이 발생하고 있어 우선 점검이 필요합니다" → 출력: {{"location": "석유제품배합/저장", "equipment_type": "Storage Tank", "status_code": "소음", "priority": "우선작업(Deadline준수)", "confidence": 0.9, "reasoning": "우선 점검 키워드로 우선작업 분류"}}

**주의사항**:
- 추출할 수 없는 정보는 null로 설정
- confidence는 0.0~1.0 사이의 값으로 설정
- 우선순위가 명시되지 않으면 "일반작업"으로 기본 설정
- 세션에서 누적된 정보가 있으면 현재 입력과 결합하여 완전한 정보 구성
- 단일 단어나 불완전한 입력도 언어 능력을 활용하여 적절한 범주로 분류
- 한국어-영어 혼용, 오타, 띄어쓰기 오류를 무시하고 의미 파악
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
            # 폴백: 간단한 추출 로직
            return {
                'location': None,
                'equipment_type': None,
                'status_code': None,
                'priority': '일반작업',
                'confidence': 0.5,
                'reasoning': '파싱 실패로 기본값 사용'
            }
    
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
            priority="일반작업",
            itemno=None,
            confidence=0.0
        )
    
    def _combine_accumulated_info(self, current_data: Dict, accumulated_info: Dict) -> Dict:
        """
        누적된 정보와 현재 정보 결합
        
        Args:
            current_data: 현재 입력에서 추출된 정보
            accumulated_info: 세션에서 누적된 정보
            
        Returns:
            결합된 정보 딕셔너리
        """
        combined_data = accumulated_info.copy() if accumulated_info else {}
        
        # 현재 입력에서 새로운 정보가 있으면 업데이트 (현재 정보 우선)
        for key in ['location', 'equipment_type', 'status_code', 'priority']:
            if current_data.get(key):
                combined_data[key] = current_data[key]
        
        return combined_data

# 전역 입력 파서 인스턴스
# 다른 모듈에서 import하여 사용
input_parser = InputParser() 