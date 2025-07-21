"""
PMark1 AI Assistant - 채팅 API

이 파일은 사용자와의 대화를 처리하는 메인 API 엔드포인트입니다.
사용자 입력을 파싱하고, 추천 엔진을 통해 유사한 작업을 찾아 응답을 생성합니다.

주요 담당자: 백엔드 개발자, API 개발자
수정 시 주의사항:
- API 응답 형식은 frontend와 호환되어야 함
- 에러 처리는 사용자 친화적으로 구현
- 로깅을 통한 디버깅 지원 필요
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models import ChatRequest, ChatResponse, ParsedInput, Recommendation
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

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    채팅 메인 엔드포인트 (세션 기반 멀티턴 대화 지원)
    
    사용자 입력을 받아 파싱하고 추천 목록을 생성하여 응답합니다.
    세션 ID가 있으면 멀티턴 대화를 지원하고, 없으면 단일 턴으로 처리합니다.
    
    Args:
        request: ChatRequest - 사용자 메시지, 대화 히스토리, 세션 ID(선택사항)
        
    Returns:
        ChatResponse - 봇 응답, 추천 목록, 파싱 결과
    """
    try:
        logger.info(f"채팅 요청 수신: {request.message[:50]}... (세션: {request.session_id})")
        
        # 1단계: 세션 관리 (세션 ID가 있는 경우)
        session_id = request.session_id
        session_state = None
        
        if session_id:
            session_state = session_manager.get_session(session_id)
            if not session_state:
                # 세션이 없으면 새로 생성
                session_id = session_manager.create_session()
                session_state = session_manager.get_session(session_id)
                logger.info(f"새 세션 생성: {session_id}")
        
        # 2단계: 사용자 입력 파싱 (세션 컨텍스트 포함)
        parsed_input = parser.parse_input(request.message, request.conversation_history, session_id)
        logger.info(f"입력 파싱 완료: 시나리오={parsed_input.scenario}, 신뢰도={parsed_input.confidence}")
        
        # 3단계: 세션 상태 업데이트 (세션이 있는 경우)
        if session_id and session_state:
            session_state = session_manager.update_session(session_id, parsed_input, request.conversation_history)
            logger.info(f"세션 상태 업데이트: {session_state.session_status}, 턴: {session_state.turn_count}")
            
            # 누적된 컨텍스트로 최종 파싱 결과 생성
            accumulated_parsed_input = session_state.accumulated_clues.to_parsed_input(parsed_input.scenario)
            
            # 누락된 필드 확인
            missing_fields = session_state.accumulated_clues.get_missing_fields()
            needs_additional_input = len(missing_fields) > 0
            
            # 추천 생성 (충분한 정보가 있는 경우에만)
            if session_state.accumulated_clues.has_sufficient_info():
                recommendations = recommender.get_recommendations(accumulated_parsed_input)
                logger.info(f"추천 생성 완료: {len(recommendations)}개")
            else:
                recommendations = []
                logger.info(f"정보 부족으로 추천 생성 안함. 누락 필드: {missing_fields}")
            
            # 세션 기반 응답 메시지 생성
            message = _create_session_response_message(session_state, recommendations, parsed_input, missing_fields)
            
        else:
            # 4단계: 기본 단일 턴 처리 (세션이 없는 경우)
            missing_fields = []
            if not parsed_input.location:
                missing_fields.append("location")
            if not parsed_input.equipment_type:
                missing_fields.append("equipment_type")
            if not parsed_input.status_code:
                missing_fields.append("status_code")
            
            needs_additional_input = len(missing_fields) > 0
            
            # 추천 생성 (충분한 정보가 있는 경우에만)
            if not needs_additional_input:
                recommendations = recommender.get_recommendations(parsed_input)
                logger.info(f"추천 생성 완료: {len(recommendations)}개")
            else:
                recommendations = []
                logger.info(f"정보 부족으로 추천 생성 안함. 누락 필드: {missing_fields}")
            
            # 기본 응답 메시지 생성
            message = _create_response_message(parsed_input, recommendations, missing_fields)
        
        # 5단계: 응답 생성
        response = ChatResponse(
            message=message,
            recommendations=recommendations,
            parsed_input=parsed_input,
            needs_additional_input=needs_additional_input,
            missing_fields=missing_fields
        )
        
        logger.info(f"채팅 응답 생성 완료: 추천 수={len(recommendations)}, 누락 필드={missing_fields}")
        return response
        
    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 사용자 친화적인 에러 응답
        return ChatResponse(
            message="죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다. 다시 시도해주세요.",
            recommendations=[],
            parsed_input=None,
            needs_additional_input=False,
            missing_fields=[]
        )

async def _handle_scenario(parsed_input: ParsedInput, user_message: str, conversation_history: list) -> ChatResponse:
    """
    시나리오별 처리 로직
    
    Args:
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
    recommendations = recommender.get_recommendations(parsed_input)
    
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
    시나리오 2 처리: ITEMNO 작업 상세 요청
    
    Args:
        parsed_input: 파싱된 입력 데이터
        user_message: 원본 사용자 메시지
        conversation_history: 대화 히스토리
        
    Returns:
        ChatResponse: 특정 작업 정보가 포함된 응답
        
    처리 로직:
    1. ITEMNO로 특정 작업 조회
    2. 작업 상세 정보 제공
    3. 관련 추천 항목 제공
    
    담당자 수정 가이드:
    - ITEMNO 검증 로직 추가 가능
    - 관련 작업 추천 로직 개선 가능
    - 작업 이력 조회 기능 추가 가능
    """
    
    if not parsed_input.itemno:
        return ChatResponse(
            message="ITEMNO를 찾을 수 없습니다. 올바른 ITEMNO를 입력해주세요.",
            recommendations=[],
            parsed_input=parsed_input,
            needs_additional_input=True,
            missing_fields=["itemno"]
        )
    
    # ITEMNO로 특정 작업 조회
    specific_recommendation = recommender.get_recommendation_by_itemno(parsed_input.itemno)
    
    if specific_recommendation:
        # 관련 추천 항목도 함께 제공
        related_recommendations = recommender.get_recommendations(parsed_input, limit=3)
        
        message = f"ITEMNO {parsed_input.itemno}에 대한 작업 정보입니다:\n\n"
        message += f"• 공정: {specific_recommendation.cost_center if specific_recommendation.cost_center else specific_recommendation.process}\n"
        message += f"• 위치: {specific_recommendation.location}\n"
        message += f"• 설비유형: {specific_recommendation.equipType}\n"
        message += f"• 현상코드: {specific_recommendation.statusCode}\n"
        message += f"• 우선순위: {specific_recommendation.priority}\n\n"
        
        if specific_recommendation.work_title:
            message += f"작업명: {specific_recommendation.work_title}\n"
        if specific_recommendation.work_details:
            message += f"작업상세: {specific_recommendation.work_details}\n"
        
        return ChatResponse(
            message=message,
            recommendations=[specific_recommendation] + related_recommendations,
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
    기본 시나리오 처리: 인식되지 않는 입력
    
    Args:
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

def _check_missing_fields(parsed_input: ParsedInput) -> list:
    """
    누락된 필드 확인
    
    Args:
        parsed_input: 파싱된 입력 데이터
        
    Returns:
        누락된 필드 리스트
        
    필수 필드:
    - location: 위치/공정
    - equipment_type: 설비유형
    - status_code: 현상코드
    
    담당자 수정 가이드:
    - 필수 필드 기준 조정 가능
    - 필드별 중요도 가중치 적용 가능
    - 신뢰도 기반 필드 검증 가능
    """
    missing_fields = []
    
    if not parsed_input.location:
        missing_fields.append("location")
    if not parsed_input.equipment_type:
        missing_fields.append("equipment_type")
    if not parsed_input.status_code:
        missing_fields.append("status_code")
    
    return missing_fields

def _create_response_message(parsed_input: ParsedInput, recommendations: List[Recommendation], missing_fields: List[str]) -> str:
    """
    기본 응답 메시지 생성 (단일 턴 또는 세션 없는 경우)
    
    Args:
        parsed_input: 파싱된 입력
        recommendations: 추천 목록
        missing_fields: 누락된 필드 목록
        
    Returns:
        응답 메시지
    """
    if parsed_input.scenario == "S2":
        # 시나리오 2: ITEMNO 기반
        if recommendations:
            return f"🎯 **{len(recommendations)}개의 유사한 작업을 찾았습니다!**\n\n아래 추천 목록에서 가장 적합한 작업을 선택해주세요."
        else:
            return "❌ **해당 ITEMNO로 유사한 작업을 찾을 수 없습니다.**\n\n다른 ITEMNO나 자연어로 작업 내용을 설명해주세요."
    
    else:
        # 시나리오 1: 자연어 기반
        if not missing_fields:
            # 충분한 정보가 있는 경우
            if recommendations:
                return f"🎯 **{len(recommendations)}개의 유사한 작업을 찾았습니다!**\n\n아래 추천 목록에서 가장 적합한 작업을 선택해주세요."
            else:
                return "❌ **입력하신 조건으로 유사한 작업을 찾을 수 없습니다.**\n\n다른 조건으로 다시 시도해주세요."
        else:
            # 정보가 부족한 경우
            message = "📝 **작업 정보를 수집하고 있습니다.**\n\n"
            
            # 파싱된 정보 표시
            if parsed_input.location:
                message += f"• 위치: {parsed_input.location} ✅\n"
            if parsed_input.equipment_type:
                message += f"• 설비유형: {parsed_input.equipment_type} ✅\n"
            if parsed_input.status_code:
                message += f"• 현상코드: {parsed_input.status_code} ✅\n"
            if parsed_input.priority and parsed_input.priority != "일반작업":
                message += f"• 우선순위: {parsed_input.priority} ✅\n"
            
            # 누락된 정보 요청
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

def _create_session_response_message(session_state, recommendations: List[Recommendation], parsed_input: ParsedInput, missing_fields: List[str]) -> str:
    """
    세션 상태 기반 응답 메시지 생성
    
    Args:
        session_state: 현재 세션 상태
        recommendations: 추천 목록
        parsed_input: 파싱된 입력
        missing_fields: 누락된 필드 목록
        
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
        # 기본 메시지
        return _create_response_message(parsed_input, recommendations, missing_fields)

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