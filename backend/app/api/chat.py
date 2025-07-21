"""
PMark2.5 AI Assistant - 채팅 API (세션 관리 기능 포함)

이 파일은 사용자와의 대화를 처리하는 메인 API 엔드포인트입니다.
사용자 입력을 파싱하고, 세션 기반 컨텍스트를 유지하며, 추천 엔진을 통해 유사한 작업을 찾아 응답을 생성합니다.

주요 담당자: 백엔드 개발자, API 개발자
수정 시 주의사항:
- 세션 관리 기능으로 멀티턴 대화 지원
- API 응답 형식은 frontend와 호환되어야 함
- 에러 처리는 사용자 친화적으로 구현
- 로깅을 통한 디버깅 지원 필요
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import ChatRequest, ChatResponse, ParsedInput, Recommendation, EnhancedChatRequest, EnhancedChatResponse
from ..agents.parser import InputParser
from ..logic.recommender import RecommendationEngine
from ..session_manager import session_manager
from ..config import Config
import logging

# API 라우터 설정
router = APIRouter()

# 로깅 설정
logger = logging.getLogger(__name__)

# 전역 인스턴스
parser = InputParser()
recommender = RecommendationEngine()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    채팅 메인 엔드포인트 (기본 호환성 유지)
    
    사용자 입력을 받아 파싱하고 추천 목록을 생성하여 응답합니다.
    기존 프론트엔드와의 호환성을 위해 유지됩니다.
    
    Args:
        request: ChatRequest - 사용자 메시지와 대화 히스토리
        
    Returns:
        ChatResponse - 봇 응답, 추천 목록, 파싱 결과
    """
    try:
        logger.info(f"채팅 요청 수신: {request.message[:50]}...")
        
        # 1단계: 사용자 입력 파싱
        parsed_input = parser.parse_input(request.message, request.conversation_history)
        logger.info(f"입력 파싱 완료: 시나리오={parsed_input.scenario}, 신뢰도={parsed_input.confidence}")
        
        # 2단계: 시나리오별 처리
        response = await _handle_scenario(parsed_input, request.message, request.conversation_history)
        
        logger.info(f"채팅 응답 생성 완료: 추천 수={len(response.recommendations)}")
        return response
        
    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        # 사용자 친화적인 에러 응답
        return ChatResponse(
            message="죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다. 다시 시도해주세요.",
            recommendations=[],
            parsed_input=None,
            needs_additional_input=False,
            missing_fields=[]
        )

@router.post("/chat/v2", response_model=EnhancedChatResponse)
async def chat_v2(request: EnhancedChatRequest):
    """
    세션 기반 채팅 엔드포인트 (PMark2.5 고급 기능)
    
    세션 관리를 통해 멀티턴 대화와 누적 컨텍스트를 지원합니다.
    
    Args:
        request: EnhancedChatRequest - 세션 ID 포함 채팅 요청
        
    Returns:
        EnhancedChatResponse - 세션 상태 포함 응답
    """
    try:
        logger.info(f"세션 기반 채팅 요청: {request.message[:50]}... (세션: {request.session_id})")
        
        # 1단계: 세션 관리
        session_id = request.session_id
        session_state = None
        
        if session_id:
            session_state = session_manager.get_session(session_id)
            if not session_state:
                # 세션이 없으면 새로 생성
                session_id = session_manager.create_session()
                session_state = session_manager.get_session(session_id)
                logger.info(f"새 세션 생성: {session_id}")
        else:
            # 세션 ID가 없으면 새로 생성
            session_id = session_manager.create_session()
            session_state = session_manager.get_session(session_id)
            logger.info(f"새 세션 생성: {session_id}")
        
        # 2단계: 사용자 입력 파싱 (컨텍스트 포함)
        parsed_input = parser.parse_input_with_context(
            request.message, 
            request.conversation_history, 
            session_id
        )
        logger.info(f"컨텍스트 파싱 완료: 시나리오={parsed_input.scenario}, 신뢰도={parsed_input.confidence}")
        
        # 3단계: 세션 상태 업데이트
        session_state = session_manager.update_session(session_id, parsed_input, request.conversation_history)
        logger.info(f"세션 상태 업데이트: {session_state.session_status}, 턴: {session_state.turn_count}")
        
        # 4단계: 누적된 컨텍스트로 최종 파싱 결과 생성
        accumulated_parsed_input = session_state.accumulated_clues.to_parsed_input(parsed_input.scenario)
        
        # 5단계: 누락된 필드 확인
        missing_fields = session_state.accumulated_clues.get_missing_fields()
        needs_additional_input = len(missing_fields) > 0
        
        # 6단계: 추천 생성 (충분한 정보가 있는 경우에만)
        if (session_state.accumulated_clues.has_sufficient_info() or 
            (parsed_input.scenario == "S2" and accumulated_parsed_input.itemno)):
            # 시나리오2는 ITEMNO만 있어도 추천 생성 가능
            recommendations = recommender.get_recommendations(accumulated_parsed_input)
            logger.info(f"추천 생성 완료: {len(recommendations)}개")
        else:
            recommendations = []
            logger.info(f"정보 부족으로 추천 생성 안함. 누락 필드: {missing_fields}")
        
        # 7단계: 세션 상태 기반 응답 메시지 생성
        message = _create_session_response_message(session_state, recommendations, parsed_input, missing_fields)
        
        # 8단계: 확장된 응답 반환
        return EnhancedChatResponse(
            message=message,
            recommendations=recommendations,
            parsed_input=parsed_input,
            needs_additional_input=needs_additional_input,
            missing_fields=missing_fields,
            session_state=session_state,
            accumulated_clues=session_state.accumulated_clues
        )
        
    except Exception as e:
        logger.error(f"세션 기반 채팅 처리 오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 기본 채팅으로 fallback
        basic_request = ChatRequest(
            message=request.message,
            conversation_history=request.conversation_history
        )
        return await chat(basic_request)

@router.post("/session-reset")
async def session_reset(session_id: str = None):
    """
    세션 초기화 엔드포인트
    
    Args:
        session_id: 초기화할 세션 ID (선택사항)
        
    Returns:
        새로운 세션 ID
    """
    try:
        # 기존 세션 삭제 (있는 경우)
        if session_id:
            session_manager.clear_session(session_id)
            logger.info(f"기존 세션 삭제: {session_id}")
        
        # 새 세션 생성
        new_session_id = session_manager.create_session()
        logger.info(f"새 세션 생성: {new_session_id}")
        
        return {
            "message": "새로운 세션이 시작되었습니다.",
            "new_session_id": new_session_id
        }
        
    except Exception as e:
        logger.error(f"세션 초기화 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 초기화 중 오류가 발생했습니다.")

@router.get("/session-stats")
async def get_session_stats():
    """
    세션 통계 조회 엔드포인트
    
    Returns:
        세션 통계 정보
    """
    try:
        stats = session_manager.get_session_stats()
        return stats
        
    except Exception as e:
        logger.error(f"세션 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 통계 조회 중 오류가 발생했습니다.")

async def _handle_scenario(parsed_input: ParsedInput, user_message: str, conversation_history: list) -> ChatResponse:
    """
    시나리오별 처리 로직
    
    Args:
        fastapi_request: FastAPI Request 객체
        parsed_input: 파싱된 입력 데이터
        user_message: 원본 사용자 메시지
        conversation_history: 대화 히스토리
        
    Returns:
        ChatResponse: 시나리오별 응답
        
    시나리오별 처리:
    - S1: 자연어 작업 요청 → 추천 목록 생성
    - S2: ITEMNO 작업 상세 요청 → 특정 작업 정보 제공
    - default: 기본 안내 메시지
    
    담당자 수정 가이드:
    - 새로운 시나리오 추가 시 이 메서드 수정
    - 각 시나리오별 처리 로직 개선 가능
    - 대화 히스토리 활용 로직 추가 가능
    """
    
    if parsed_input.scenario == "S1":
        return await _handle_scenario_1(parsed_input, user_message, conversation_history)
    elif parsed_input.scenario == "S2":
        return await _handle_scenario_2(parsed_input, user_message, conversation_history)
    else:
        return await _handle_default_scenario(parsed_input, user_message, conversation_history)

async def _handle_scenario_1(parsed_input: ParsedInput, user_message: str, conversation_history: list) -> ChatResponse:
    """
    시나리오 1 처리: 자연어 작업 요청
    
    Args:
        fastapi_request: FastAPI Request 객체
        parsed_input: 파싱된 입력 데이터
        user_message: 원본 사용자 메시지
        conversation_history: 대화 히스토리
        
    Returns:
        ChatResponse: 추천 목록이 포함된 응답
        
    처리 로직:
    1. 누락된 필드 확인
    2. 추천 엔진 호출
    3. 응답 메시지 생성
    
    담당자 수정 가이드:
    - 추천 수 조정 가능 (현재 5개)
    - 누락 필드 처리 로직 개선 가능
    - 응답 메시지 개인화 가능
    """
    
    # 누락된 필드 확인
    missing_fields = _check_missing_fields(parsed_input)
    
    # 추천 엔진 호출
    if not missing_fields:
        recommendations = recommender.get_recommendations(parsed_input)
    else:
        recommendations = []
    
    # 응답 메시지 생성
    message = _create_response_message(parsed_input, recommendations, missing_fields)
    
    return ChatResponse(
        message=message,
        recommendations=recommendations,
        parsed_input=parsed_input,
        needs_additional_input=len(missing_fields) > 0,
        missing_fields=missing_fields
    )

async def _handle_scenario_2(parsed_input: ParsedInput, user_message: str, conversation_history: list) -> ChatResponse:
    """
    시나리오 2 처리: ITEMNO 기반 작업 상세 요청
    
    Args:
        fastapi_request: FastAPI Request 객체
        parsed_input: 파싱된 입력 데이터
        user_message: 원본 사용자 메시지
        conversation_history: 대화 히스토리
        
    Returns:
        ChatResponse: 특정 작업 정보가 포함된 응답
        
    처리 로직:
    1. ITEMNO 유효성 검증
    2. 추천 엔진 호출
    3. 응답 메시지 생성
    """
    if parsed_input.itemno:
        recommendations = recommender.get_recommendations(parsed_input, limit=1)
    else:
        recommendations = []
    
    if recommendations:
        # 관련 추천 항목도 함께 제공
        related_recommendations = recommender.get_recommendations(parsed_input, limit=3)
        
        message = f"ITEMNO {parsed_input.itemno}에 대한 작업 정보입니다:\n\n"
        message += f"• 공정: {recommendations[0].process}\n" # Assuming recommendations[0] is the specific one
        message += f"• 위치: {recommendations[0].location}\n" # Assuming recommendations[0] is the specific one
        message += f"• 설비유형: {recommendations[0].equipType}\n" # Assuming recommendations[0] is the specific one
        message += f"• 현상코드: {recommendations[0].statusCode}\n" # Assuming recommendations[0] is the specific one
        message += f"• 우선순위: {recommendations[0].priority}\n\n" # Assuming recommendations[0] is the specific one
        
        if recommendations[0].work_title:
            message += f"작업명: {recommendations[0].work_title}\n" # Assuming recommendations[0] is the specific one
        if recommendations[0].work_details:
            message += f"작업상세: {recommendations[0].work_details}\n" # Assuming recommendations[0] is the specific one
        
        return ChatResponse(
            message=message,
            recommendations=[recommendations[0]] + related_recommendations,
            parsed_input=parsed_input,
            needs_additional_input=False,
            missing_fields=[]
        )
    else:
        return ChatResponse(
            message=f"ITEMNO {parsed_input.itemno}에 해당하는 작업을 찾을 수 없습니다.",
            recommendations=[],
            parsed_input=parsed_input,
            needs_additional_input=True,
            missing_fields=["itemno"]
        )

async def _handle_default_scenario(parsed_input: ParsedInput, user_message: str, conversation_history: list) -> ChatResponse:
    """
    시나리오 3 (기본) 처리: 정보 부족 안내
    
    Args:
        fastapi_request: FastAPI Request 객체
        parsed_input: 파싱된 입력 데이터
        user_message: 원본 사용자 메시지
        conversation_history: 대화 히스토리
        
    Returns:
        ChatResponse: 안내 메시지가 포함된 응답
        
    담당자 수정 가이드:
    - 사용자 안내 메시지 개선 가능
    - 예시 제공 로직 추가 가능
    - 대화 히스토리 기반 컨텍스트 파악 가능
    """
    
    message = "안녕하세요! 설비관리 작업요청을 도와드리겠습니다.\n\n"
    message += "다음과 같은 형식으로 입력해주세요:\n"
    message += "• \"1PE 압력베젤 고장\" - 자연어로 작업 요청\n"
    message += "• \"ITEMNO 12345\" - 특정 작업 상세 조회\n\n"
    message += "**위치 정보를 포함하면 더 정확한 추천을 받을 수 있습니다.**\n"
    message += "예시: \"No.1 PE 압력베젤 고장\", \"석유제품배합/저장 탱크 누설\"\n\n"
    message += "어떤 작업을 도와드릴까요?"
    
    return ChatResponse(
        message=message,
        recommendations=[],
        parsed_input=parsed_input,
        needs_additional_input=True,
        missing_fields=[]
    )

def _create_session_response_message(session_state, recommendations: List[Recommendation], parsed_input: ParsedInput, missing_fields: List[str]) -> str:
    """
    세션 상태 기반 응답 메시지 생성
    
    Args:
        session_state: 현재 세션 상태
        recommendations: 추천 목록
        parsed_input: 파싱된 입력
        missing_fields: 누락된 필드들
        
    Returns:
        세션 컨텍스트를 반영한 응답 메시지
    """
    accumulated_clues = session_state.accumulated_clues
    
    # 세션 상태별 메시지 생성
    if session_state.session_status == "collecting_info":
        # 정보 수집 단계
        message = "📝 **작업 정보를 수집하고 있습니다.**\n\n"
        
        # 누적된 정보 표시
        if accumulated_clues.location:
            message += f"• 위치: {accumulated_clues.location} ✅\n"
        if accumulated_clues.equipment_type:
            message += f"• 설비유형: {accumulated_clues.equipment_type} ✅\n"
        if accumulated_clues.status_code:
            message += f"• 현상코드: {accumulated_clues.status_code} ✅\n"
        if accumulated_clues.priority and accumulated_clues.priority != "일반작업":
            message += f"• 우선순위: {accumulated_clues.priority} ✅\n"
        
        # 누락된 정보 요청
        if missing_fields:
            message += f"\n❗ **추가로 필요한 정보:**\n"
            for field in missing_fields:
                if field == "location":
                    message += "• 위치/공정 (예: No.1 PE, No.2 PE, 석유제품배합/저장)\n"
                elif field == "equipment_type":
                    message += "• 설비유형 (예: 압력베젤, 펌프, 열교환기, 탱크, 밸브)\n"
                elif field == "status_code":
                    message += "• 현상코드 (예: 고장, 누설, 작동불량, 소음, 진동)\n"
            
            message += "\n💡 **또는 작업대상(ITEMNO)과 현상코드를 직접 입력하셔도 됩니다.**"
        
        return message
    
    elif session_state.session_status == "recommending":
        # 추천 단계
        message = f"🎯 **{len(recommendations)}개의 유사한 작업을 찾았습니다!**\n\n"
        
        # 누적된 정보 요약
        message += "📋 **수집된 정보:**\n"
        if accumulated_clues.location:
            message += f"• 위치: {accumulated_clues.location}\n"
        if accumulated_clues.equipment_type:
            message += f"• 설비유형: {accumulated_clues.equipment_type}\n"
        if accumulated_clues.status_code:
            message += f"• 현상코드: {accumulated_clues.status_code}\n"
        if accumulated_clues.priority and accumulated_clues.priority != "일반작업":
            message += f"• 우선순위: {accumulated_clues.priority}\n"
        
        message += f"\n💡 **턴 {session_state.turn_count}**: 아래 추천 목록에서 가장 적합한 작업을 선택해주세요."
        
        return message
    
    elif session_state.session_status == "finalizing":
        # 완료 단계
        message = "✅ **작업 정보가 완성되었습니다!**\n\n"
        message += "선택하신 작업으로 작업요청을 생성하시겠습니까?"
        
        return message
    
    else:
        # 기본 메시지 - 기존 로직 사용
        message = "📝 **작업 정보를 수집하고 있습니다.**\n\n"
        
        # 누적된 정보 표시
        if accumulated_clues.location:
            message += f"• 위치: {accumulated_clues.location} ✅\n"
        if accumulated_clues.equipment_type:
            message += f"• 설비유형: {accumulated_clues.equipment_type} ✅\n"
        if accumulated_clues.status_code:
            message += f"• 현상코드: {accumulated_clues.status_code} ✅\n"
        if accumulated_clues.priority and accumulated_clues.priority != "일반작업":
            message += f"• 우선순위: {accumulated_clues.priority} ✅\n"
        
        # 누락된 정보 요청
        if missing_fields:
            message += f"\n❗ **추가로 필요한 정보:**\n"
            for field in missing_fields:
                if field == "location":
                    message += "• 위치/공정 (예: No.1 PE, No.2 PE, 석유제품배합/저장)\n"
                elif field == "equipment_type":
                    message += "• 설비유형 (예: 압력베젤, 펌프, 열교환기, 탱크, 밸브)\n"
                elif field == "status_code":
                    message += "• 현상코드 (예: 고장, 누설, 작동불량, 소음, 진동)\n"
            
            message += "\n💡 **또는 작업대상(ITEMNO)과 현상코드를 직접 입력하셔도 됩니다.**"
        
        return message

def _create_response_message(parsed_input: ParsedInput, recommendations: List[Recommendation], missing_fields: List[str]) -> str:
    """
    기본 응답 메시지 생성 (기존 호환성 유지)
    
    Args:
        parsed_input: 파싱된 입력 데이터
        recommendations: 추천 목록
        missing_fields: 누락된 필드들
        
    Returns:
        응답 메시지
    """
    if not recommendations:
        return "죄송합니다. 입력하신 조건에 맞는 작업을 찾을 수 없습니다. 다른 키워드로 다시 시도해주세요."
    
    # 기본 응답 메시지
    message = f"🎯 **{len(recommendations)}개의 유사한 작업을 찾았습니다!**\n\n"
    
    # 파싱된 정보 표시
    if parsed_input.location:
        message += f"• 위치/공정: {parsed_input.location}\n"
    if parsed_input.equipment_type:
        message += f"• 설비유형: {parsed_input.equipment_type}\n"
    if parsed_input.status_code:
        message += f"• 현상코드: {parsed_input.status_code}\n"
    if parsed_input.priority:
        message += f"• 우선순위: {parsed_input.priority}\n"
    
    # 누락된 정보 안내
    if missing_fields:
        message += f"\n❓ **추가 정보가 있으면 더 정확한 추천이 가능합니다:**\n"
        for field in missing_fields:
            if field == "location":
                message += "• 위치/공정 정보\n"
            elif field == "equipment_type":
                message += "• 설비유형 정보\n"
            elif field == "status_code":
                message += "• 현상코드 정보\n"
    
    message += f"\n💡 아래 추천 목록에서 가장 적합한 작업을 선택해주세요."
    
    return message

def _check_missing_fields(parsed_input: ParsedInput) -> List[str]:
    """
    누락된 필드 확인
    
    Args:
        parsed_input: 파싱된 입력 데이터
        
    Returns:
        누락된 필드명 리스트
    """
    missing = []
    if not parsed_input.location:
        missing.append("location")
    if not parsed_input.equipment_type:
        missing.append("equipment_type")
    if not parsed_input.status_code:
        missing.append("status_code")
    return missing 