"""
PMark1 AI Assistant - 데이터 모델 정의

이 파일은 PMark1 AI Assistant의 모든 데이터 모델을 정의합니다.
각 모델은 Pydantic BaseModel을 상속받아 자동 검증과 직렬화를 지원합니다.

주요 담당자: 백엔드 개발자
수정 시 주의사항: 
- 모델 변경 시 API 스키마가 자동으로 업데이트됩니다
- Recommendation 모델의 priority 필드는 필수입니다 (finalize-work-order API에서 사용)
- 새로운 필드 추가 시 기본값 설정을 권장합니다
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """
    채팅 메시지 모델
    
    사용처: 
    - chat.py: 대화 히스토리 저장
    - parser.py: 컨텍스트 분석용
    
    연계 파일:
    - ChatRequest.conversation_history에서 사용
    - ChatResponse에서 응답 메시지 생성
    """
    role: str = Field(..., description="메시지 역할 (user/assistant)")
    content: str = Field(..., description="메시지 내용")
    timestamp: Optional[str] = Field(None, description="타임스탬프")

class ChatRequest(BaseModel):
    """
    채팅 요청 모델
    
    사용처:
    - chat.py: POST /api/v1/chat 엔드포인트
    - parser.py: 사용자 입력 분석
    
    연계 파일:
    - InputParser.parse_input()에서 user_input으로 사용
    - RecommendationEngine.get_recommendations()에서 parsed_input 전달
    """
    message: str = Field(..., description="사용자 입력 메시지")
    conversation_history: List[ChatMessage] = Field(default=[], description="대화 히스토리")
    session_id: Optional[str] = Field(None, description="세션 ID (누적 정보 관리용)")

class AccumulatedClues(BaseModel):
    """
    누적된 단서 항목들 모델
    
    사용처:
    - SessionState 내부에서 단서 항목 관리
    - parser.py에서 이전 컨텍스트와 병합
    
    담당자 수정 가이드:
    - 각 필드는 Optional이며 점진적으로 채워짐
    - confidence는 각 항목의 신뢰도 추적
    - merge_with() 메서드로 새 정보와 병합
    """
    location: Optional[str] = Field(None, description="누적된 위치/공정")
    equipment_type: Optional[str] = Field(None, description="누적된 설비유형")
    status_code: Optional[str] = Field(None, description="누적된 현상코드")
    priority: Optional[str] = Field(None, description="누적된 우선순위")
    itemno: Optional[str] = Field(None, description="누적된 ITEMNO")
    
    # 각 항목별 신뢰도 추적
    location_confidence: float = Field(default=0.0, description="위치 신뢰도")
    equipment_type_confidence: float = Field(default=0.0, description="설비유형 신뢰도")
    status_code_confidence: float = Field(default=0.0, description="현상코드 신뢰도")
    priority_confidence: float = Field(default=0.0, description="우선순위 신뢰도")
    
    def merge_with(self, parsed_input: "ParsedInput") -> "AccumulatedClues":
        """
        새로운 ParsedInput과 기존 누적 정보를 병합
        
        Args:
            parsed_input: 새로 파싱된 입력 정보
            
        Returns:
            병합된 AccumulatedClues 객체
            
        병합 규칙:
        1. 새 정보가 있고 신뢰도가 높으면 업데이트
        2. 기존 정보가 없으면 새 정보로 설정
        3. 신뢰도가 비슷하면 기존 정보 유지 (사용자 의도 존중)
        """
        merged = AccumulatedClues(
            location=self.location,
            equipment_type=self.equipment_type,
            status_code=self.status_code,
            priority=self.priority,
            itemno=self.itemno,
            location_confidence=self.location_confidence,
            equipment_type_confidence=self.equipment_type_confidence,
            status_code_confidence=self.status_code_confidence,
            priority_confidence=self.priority_confidence
        )
        
        # 위치 정보 병합
        if parsed_input.location and (
            not merged.location or 
            parsed_input.confidence > merged.location_confidence + 0.1
        ):
            merged.location = parsed_input.location
            merged.location_confidence = parsed_input.confidence
            
        # 설비유형 병합
        if parsed_input.equipment_type and (
            not merged.equipment_type or 
            parsed_input.confidence > merged.equipment_type_confidence + 0.1
        ):
            merged.equipment_type = parsed_input.equipment_type
            merged.equipment_type_confidence = parsed_input.confidence
            
        # 현상코드 병합
        if parsed_input.status_code and (
            not merged.status_code or 
            parsed_input.confidence > merged.status_code_confidence + 0.1
        ):
            merged.status_code = parsed_input.status_code
            merged.status_code_confidence = parsed_input.confidence
            
        # 우선순위 병합 (기본값이 아닌 경우만)
        if parsed_input.priority and parsed_input.priority != "일반작업" and (
            not merged.priority or 
            parsed_input.confidence > merged.priority_confidence + 0.1
        ):
            merged.priority = parsed_input.priority
            merged.priority_confidence = parsed_input.confidence
            
        # ITEMNO 병합 (시나리오 2용)
        if parsed_input.itemno:
            merged.itemno = parsed_input.itemno
            
        return merged
    
    def to_parsed_input(self, scenario: str = "S1") -> "ParsedInput":
        """
        누적된 단서를 ParsedInput 형태로 변환
        
        Args:
            scenario: 시나리오 타입
            
        Returns:
            누적된 정보가 포함된 ParsedInput 객체
        """
        # 전체 신뢰도 계산 (각 항목 신뢰도의 평균)
        confidences = [
            self.location_confidence if self.location else 0.0,
            self.equipment_type_confidence if self.equipment_type else 0.0,
            self.status_code_confidence if self.status_code else 0.0,
            self.priority_confidence if self.priority else 0.0
        ]
        
        valid_confidences = [c for c in confidences if c > 0.0]
        avg_confidence = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.0
        
        return ParsedInput(
            scenario=scenario,
            location=self.location,
            equipment_type=self.equipment_type,
            status_code=self.status_code,
            priority=self.priority or "일반작업",
            itemno=self.itemno,
            confidence=avg_confidence
        )
    
    def get_missing_fields(self) -> List[str]:
        """
        누락된 주요 필드들 반환
        
        Returns:
            누락된 필드명 리스트
        """
        missing = []
        if not self.location:
            missing.append("location")
        if not self.equipment_type:
            missing.append("equipment_type")
        if not self.status_code:
            missing.append("status_code")
        return missing
    
    def has_sufficient_info(self) -> bool:
        """
        충분한 정보가 있는지 확인 (3개 필수 단서 모두 존재)
        
        Returns:
            충분한 정보 존재 여부
        """
        return bool(self.location and self.equipment_type and self.status_code)

class SessionState(BaseModel):
    """
    멀티턴 대화 세션 상태 모델
    
    사용처:
    - chat.py: 세션별 컨텍스트 유지
    - parser.py: 누적된 단서 항목 참조
    
    담당자 수정 가이드:
    - accumulated_clues는 대화 중 누적된 단서 항목들
    - session_status는 세션 진행 상태 추적
    - 새 세션 시작 시 모든 필드 초기화
    """
    session_id: str = Field(..., description="세션 고유 ID")
    accumulated_clues: AccumulatedClues = Field(default_factory=AccumulatedClues, description="누적된 단서 항목들")
    session_status: str = Field(default="collecting_info", description="세션 상태 (collecting_info/recommending/finalizing)")
    created_at: datetime = Field(default_factory=datetime.now, description="세션 생성일시")
    last_updated: datetime = Field(default_factory=datetime.now, description="마지막 업데이트 시간")
    turn_count: int = Field(default=0, description="대화 턴 수")

class ParsedInput(BaseModel):
    """
    구문분석 결과 모델
    
    사용처:
    - parser.py: LLM 분석 결과 저장
    - recommender.py: 추천 엔진 입력
    - chat.py: 응답 생성
    
    연계 파일:
    - InputParser.parse_input()에서 반환
    - RecommendationEngine.get_recommendations()에서 입력으로 사용
    - ChatResponse.parsed_input으로 응답에 포함
    
    담당자 수정 가이드:
    - 새로운 필드 추가 시 parser.py의 _create_scenario_1_prompt()도 수정 필요
    - confidence 필드는 LLM 응답의 신뢰도를 나타냄 (0.0~1.0)
    - missing_items는 시나리오 1에서 누락된 주요 3개 단서 항목 목록
    - needs_additional_input은 추가 입력이 필요한지 여부
    """
    scenario: str = Field(..., description="시나리오 (S1/S2)")
    location: Optional[str] = Field(None, description="위치/공정")
    equipment_type: Optional[str] = Field(None, description="설비유형")
    status_code: Optional[str] = Field(None, description="현상코드")
    priority: str = Field(default="일반작업", description="우선순위")
    itemno: Optional[str] = Field(None, description="ITEMNO (시나리오 2용)")
    confidence: float = Field(..., description="분석 신뢰도")
    missing_items: List[str] = Field(default=[], description="누락된 주요 단서 항목들 (location, equipment_type, status_code)")
    needs_additional_input: bool = Field(default=False, description="추가 입력 필요 여부")

class Recommendation(BaseModel):
    """
    추천 항목 모델
    
    사용처:
    - recommender.py: 추천 결과 생성
    - work_details.py: 작업상세 생성
    - chat.py: 추천 목록 응답
    
    연계 파일:
    - RecommendationEngine._convert_to_recommendations()에서 생성
    - WorkDetailsRequest.selected_recommendation에서 사용
    - FinalizeRequest.selected_recommendation에서 사용
    
    중요: priority 필드는 finalize-work-order API에서 필수로 사용됩니다!
    
    담당자 수정 가이드:
    - 새로운 필드 추가 시 recommender.py의 _convert_to_recommendations() 수정 필요
    - work_title, work_details는 LLM이 생성하는 필드
    - score는 유사도 점수 (0.0~1.0)
    """
    itemno: str = Field(..., description="ITEMNO")
    process: str = Field(..., description="공정명")
    location: str = Field(..., description="위치")
    cost_center: Optional[str] = Field(None, description="Cost Center (공정명 표시용)")
    equipType: str = Field(..., description="설비유형")
    statusCode: str = Field(..., description="현상코드")
    priority: str = Field(default="일반작업", description="우선순위")
    score: float = Field(..., description="유사도 점수")
    work_title: Optional[str] = Field(None, description="작업명")
    work_details: Optional[str] = Field(None, description="작업상세")

class ChatResponse(BaseModel):
    """
    채팅 응답 모델
    
    사용처:
    - chat.py: POST /api/v1/chat 응답
    - frontend: 채팅 인터페이스 표시
    
    연계 파일:
    - chat.py의 chat_endpoint()에서 반환
    - frontend에서 추천 목록과 구문분석 결과 표시
    
    담당자 수정 가이드:
    - message 필드는 사용자에게 보여질 메시지
    - recommendations는 선택 가능한 추천 항목들
    - needs_additional_input은 추가 입력 필요 여부
    """
    message: str = Field(..., description="봇 응답 메시지")
    recommendations: List[Recommendation] = Field(default=[], description="추천 항목들")
    parsed_input: Optional[ParsedInput] = Field(None, description="구문분석 결과")
    needs_additional_input: bool = Field(default=False, description="추가 입력 필요 여부")
    missing_fields: List[str] = Field(default=[], description="누락된 필드들")

class WorkDetailsRequest(BaseModel):
    """
    작업상세 생성 요청 모델
    
    사용처:
    - work_details.py: POST /api/v1/generate-work-details
    
    연계 파일:
    - frontend에서 선택된 추천 항목과 사용자 메시지 전송
    - work_details.py의 generate_work_details()에서 처리
    
    담당자 수정 가이드:
    - selected_recommendation은 사용자가 선택한 추천 항목
    - user_message는 원본 사용자 입력 (LLM 컨텍스트용)
    """
    selected_recommendation: Recommendation = Field(..., description="선택된 추천 항목")
    user_message: str = Field(..., description="사용자 원본 메시지")

class WorkDetailsResponse(BaseModel):
    """
    작업상세 생성 응답 모델
    
    사용처:
    - work_details.py: POST /api/v1/generate-work-details 응답
    - frontend: 생성된 작업명/상세 표시
    
    연계 파일:
    - work_details.py의 generate_work_details()에서 반환
    - frontend에서 최종 작업요청 완성 단계로 전달
    
    담당자 수정 가이드:
    - work_title은 LLM이 생성한 작업명 (20자 이내 권장)
    - work_details는 LLM이 생성한 작업상세 (100자 이내 권장)
    """
    work_title: str = Field(..., description="생성된 작업명")
    work_details: str = Field(..., description="생성된 작업상세")

class FinalizeRequest(BaseModel):
    """
    최종 작업요청 완성 요청 모델
    
    사용처:
    - work_details.py: POST /api/v1/finalize-work-order
    
    연계 파일:
    - frontend에서 최종 확인 후 전송
    - work_details.py의 finalize_work_order()에서 처리
    
    담당자 수정 가이드:
    - work_title, work_details는 사용자가 수정한 최종 내용
    - selected_recommendation은 원본 추천 항목 (DB 저장용)
    """
    work_title: str = Field(..., description="작업명")
    work_details: str = Field(..., description="작업상세")
    selected_recommendation: Recommendation = Field(..., description="선택된 추천 항목")
    user_message: str = Field(..., description="사용자 원본 메시지")

class WorkOrder(BaseModel):
    """
    작업요청 모델 (최종 완성된 형태)
    
    사용처:
    - work_details.py: 최종 작업요청 저장
    - database.py: DB 저장용 (향후 구현)
    
    연계 파일:
    - work_details.py의 finalize_work_order()에서 생성
    - FinalizeResponse.work_order로 반환
    
    담당자 수정 가이드:
    - itemno는 자동 생성되는 작업요청번호
    - created_at은 자동으로 현재 시간 설정
    - 향후 Kafka 연동 시 이 모델을 사용하여 전송
    """
    itemno: str = Field(..., description="작업요청번호")
    work_title: str = Field(..., description="작업명")
    work_details: str = Field(..., description="작업상세")
    process: str = Field(..., description="공정명")
    location: str = Field(..., description="위치")
    equipType: str = Field(..., description="설비유형")
    statusCode: str = Field(..., description="현상코드")
    priority: str = Field(..., description="우선순위")
    created_at: datetime = Field(default_factory=datetime.now, description="생성일시")

class FinalizeResponse(BaseModel):
    """
    최종 작업요청 완성 응답 모델
    
    사용처:
    - work_details.py: POST /api/v1/finalize-work-order 응답
    - frontend: 완성 메시지 표시
    
    연계 파일:
    - work_details.py의 finalize_work_order()에서 반환
    - frontend에서 완료 메시지 표시
    
    담당자 수정 가이드:
    - message는 사용자에게 보여질 완료 메시지
    - work_order는 완성된 작업요청 정보
    """
    message: str = Field(..., description="완성 메시지")
    work_order: WorkOrder = Field(..., description="완성된 작업요청") 