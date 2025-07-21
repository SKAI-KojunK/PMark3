"""
PMark1 AI Assistant - 작업상세 API

이 파일은 선택된 추천 항목에 대한 작업상세 생성과 최종 작업요청 완성을 처리하는 API입니다.
LLM을 활용하여 작업명과 상세를 생성하고, 최종 작업요청을 완성합니다.

주요 담당자: 백엔드 개발자, API 개발자
수정 시 주의사항:
- 작업상세 생성 품질은 LLM 프롬프트에 의존
- 최종 작업요청은 외부 시스템과 연동 필요
- 트랜잭션 처리 및 롤백 로직 고려
"""

from fastapi import APIRouter, HTTPException
from ..models import (
    WorkDetailsRequest, WorkDetailsResponse, 
    FinalizeRequest, FinalizeResponse, WorkOrder
)
from ..logic.recommender import recommendation_engine
from ..database import db_manager
from ..session_manager import session_manager
from openai import OpenAI
from ..config import Config
import logging
from datetime import datetime
import uuid

# API 라우터 설정
router = APIRouter(tags=["work-details"])

# 로깅 설정
logger = logging.getLogger(__name__)

# OpenAI 설정 (제거됨 - 각 함수에서 개별적으로 설정)

@router.post("/generate-work-details", response_model=WorkDetailsResponse)
async def generate_work_details(request: WorkDetailsRequest):
    """
    작업상세 생성 엔드포인트
    
    선택된 추천 항목을 기반으로 LLM이 작업명과 상세를 생성합니다.
    
    Args:
        request: WorkDetailsRequest - 선택된 추천 항목과 사용자 메시지
        
    Returns:
        WorkDetailsResponse - 생성된 작업명과 상세
        
    사용처:
    - frontend: 사용자가 추천 항목 선택 후 작업상세 생성
    - 모바일 앱: 동일한 API 사용 가능
        
    연계 파일:
    - models.py: WorkDetailsRequest, WorkDetailsResponse 모델 사용
    - logic/recommender.py: recommendation_engine 활용
    - config.py: OpenAI API 설정
    
    API 흐름:
    1. 선택된 추천 항목 검증
    2. LLM을 사용한 작업상세 생성
    3. 생성된 내용 검증
    4. 응답 반환
    
    담당자 수정 가이드:
    - LLM 프롬프트 수정으로 생성 품질 향상 가능
    - 작업명/상세 길이 제한 조정 가능
    - 특정 설비유형별 맞춤 프롬프트 사용 가능
    - 생성 결과 검증 로직 추가 가능
    """
    try:
        logger.info(f"작업상세 생성 요청: ITEMNO={request.selected_recommendation.itemno}")
        
        # 1단계: 선택된 추천 항목 검증
        if not request.selected_recommendation:
            raise HTTPException(status_code=400, detail="선택된 추천 항목이 없습니다.")
        
        # 2단계: LLM을 사용한 작업상세 생성
        work_details = await _generate_work_details_with_llm(
            request.selected_recommendation, 
            request.user_message
        )
        
        # 3단계: 생성된 내용 검증
        if not work_details.get('work_title') or not work_details.get('work_details'):
            raise HTTPException(status_code=500, detail="작업상세 생성에 실패했습니다.")
        
        logger.info(f"작업상세 생성 완료: {work_details['work_title']}")
        
        return WorkDetailsResponse(
            work_title=work_details['work_title'],
            work_details=work_details['work_details']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업상세 생성 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")

@router.post("/finalize-work-order", response_model=FinalizeResponse)
async def finalize_work_order(request: FinalizeRequest):
    """
    최종 작업요청 완성 엔드포인트
    
    사용자가 수정한 작업명과 상세를 포함하여 최종 작업요청을 완성합니다.
    
    Args:
        request: FinalizeRequest - 최종 작업명, 상세, 선택된 추천 항목
        
    Returns:
        FinalizeResponse - 완성된 작업요청 정보
        
    사용처:
    - frontend: 사용자가 작업상세 수정 후 최종 완성
    - 외부 시스템: 완성된 작업요청을 다른 시스템으로 전송
        
    연계 파일:
    - models.py: FinalizeRequest, FinalizeResponse, WorkOrder 모델 사용
    - database.py: db_manager.save_work_order() 호출
    - 외부 시스템: 향후 Kafka 연동 등
    
    API 흐름:
    1. 입력 데이터 검증
    2. 작업요청 번호 생성
    3. 최종 작업요청 객체 생성
    4. 데이터베이스 저장 (향후 외부 시스템 연동)
    5. 완성 응답 반환
    
    담당자 수정 가이드:
    - ITEMNO 생성 규칙 변경 가능
    - 외부 시스템 연동 로직 추가 필요
    - 트랜잭션 처리 및 롤백 로직 구현 필요
    - 감사 로그(Audit Log) 추가 권장
    """
    try:
        logger.info(f"작업요청 완성 요청: {request.work_title}")
        
        # 1단계: 입력 데이터 검증
        if not request.work_title or not request.work_details:
            raise HTTPException(status_code=400, detail="작업명과 작업상세는 필수입니다.")
        
        if not request.selected_recommendation:
            raise HTTPException(status_code=400, detail="선택된 추천 항목이 없습니다.")
        
        # 2단계: 작업요청 번호 생성 (실제 운영에서는 외부 시스템에서 생성)
        work_order_itemno = _generate_work_order_itemno()
        
        # 3단계: 최종 작업요청 객체 생성
        work_order = WorkOrder(
            itemno=work_order_itemno,
            work_title=request.work_title,
            work_details=request.work_details,
            process=request.selected_recommendation.process,
            location=request.selected_recommendation.location,
            equipType=request.selected_recommendation.equipType,
            statusCode=request.selected_recommendation.statusCode,
            priority=request.selected_recommendation.priority,
            created_at=datetime.now()
        )
        
        # 4단계: 데이터베이스 저장 (향후 외부 시스템 연동)
        save_success = db_manager.save_work_order(work_order.dict())
        
        if not save_success:
            raise HTTPException(status_code=500, detail="작업요청 저장에 실패했습니다.")
        
        # 5단계: 완성 응답 생성
        completion_message = _create_completion_message(work_order)
        
        logger.info(f"작업요청 완성 성공: ITEMNO={work_order_itemno}")
        
        return FinalizeResponse(
            message=completion_message,
            work_order=work_order
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업요청 완성 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")

@router.post("/finalize-work-order-v2", response_model=FinalizeResponse)
async def finalize_work_order_v2(request: FinalizeRequest, session_id: str = None):
    """
    세션 기반 작업요청 완성 엔드포인트 (v2.5 신기능)
    
    작업 완료 시 자동으로 세션을 종료하여 새로운 작업 세션을 준비합니다.
    
    Args:
        request: FinalizeRequest - 최종 작업명, 상세, 선택된 추천 항목
        session_id: 현재 작업 세션 ID (선택사항)
        
    Returns:
        FinalizeResponse - 완성된 작업요청 정보
        
    사용처:
    - frontend: 세션 기반 채팅에서 작업 완성
    - 멀티턴 대화 컨텍스트 관리
        
    API 흐름:
    1. 기본 작업요청 완성 처리
    2. 세션 종료 및 정리
    3. 새 세션 준비 안내
    4. 완성 응답 반환
    
    담당자 수정 가이드:
    - 기존 finalize_work_order와 병행 운영
    - 세션 정리 로직은 session_manager에서 처리
    - 외부 시스템 연동 시 트랜잭션 고려
    """
    try:
        logger.info(f"세션 기반 작업요청 완성 요청: {request.work_title} (세션: {session_id})")
        
        # 1단계: 기본 작업요청 완성 처리 (기존 로직 재사용)
        basic_response = await finalize_work_order(request)
        
        # 2단계: 세션 종료 처리
        if session_id:
            session_state = session_manager.get_session(session_id)
            if session_state:
                # 세션 완료 마킹
                finalize_success = session_manager.finalize_session(session_id)
                
                if finalize_success:
                    logger.info(f"세션 종료 완료: {session_id}")
                    
                    # 세션 통계 로깅
                    session_stats = {
                        "session_id": session_id,
                        "turn_count": session_state.turn_count,
                        "session_duration": str(datetime.now() - session_state.created_at),
                        "final_clues": {
                            "location": session_state.accumulated_clues.location,
                            "equipment_type": session_state.accumulated_clues.equipment_type,
                            "status_code": session_state.accumulated_clues.status_code,
                            "priority": session_state.accumulated_clues.priority
                        }
                    }
                    logger.info(f"세션 완료 통계: {session_stats}")
                else:
                    logger.warning(f"세션 종료 실패: {session_id}")
            else:
                logger.warning(f"세션을 찾을 수 없음: {session_id}")
        
        # 3단계: 완성 메시지에 새 세션 안내 추가
        enhanced_message = basic_response.message + "\n\n"
        enhanced_message += "🎉 **작업요청이 성공적으로 완성되었습니다!**\n\n"
        enhanced_message += "새로운 작업이 있으시면 언제든지 말씀해주세요.\n"
        enhanced_message += "이전 대화 내용은 초기화되며, 새로운 세션으로 시작됩니다."
        
        # 4단계: 완성 응답 반환
        return FinalizeResponse(
            message=enhanced_message,
            work_order=basic_response.work_order
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 기반 작업요청 완성 오류: {e}")
        # 기본 완성 로직으로 fallback
        try:
            return await finalize_work_order(request)
        except:
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")

@router.post("/session-reset")
async def reset_session(session_id: str = None):
    """
    세션 수동 리셋 엔드포인트
    
    사용자가 명시적으로 새 작업을 시작하고 싶을 때 세션을 리셋합니다.
    
    Args:
        session_id: 리셋할 세션 ID
        
    Returns:
        새로운 세션 정보
        
    사용처:
    - frontend: "새 작업" 버튼 클릭 시
    - 사용자가 이전 대화 내용을 지우고 싶을 때
    """
    try:
        logger.info(f"세션 수동 리셋 요청: {session_id}")
        
        # 기존 세션 종료
        if session_id:
            session_manager.end_session(session_id)
            logger.info(f"기존 세션 종료: {session_id}")
        
        # 새 세션 생성
        new_session_id = session_manager.create_session()
        logger.info(f"새 세션 생성: {new_session_id}")
        
        return {
            "message": "새로운 작업 세션이 시작되었습니다. 작업요청을 입력해주세요.",
            "new_session_id": new_session_id,
            "reset_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"세션 리셋 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 리셋에 실패했습니다.")

@router.get("/session-stats")
async def get_session_stats():
    """
    세션 통계 조회 엔드포인트
    
    현재 활성 세션들의 통계 정보를 반환합니다.
    
    Returns:
        세션 통계 정보
        
    사용처:
    - 관리자 모니터링
    - 시스템 성능 분석
    """
    try:
        stats = session_manager.get_session_stats()
        
        return {
            "session_stats": stats,
            "timestamp": datetime.now().isoformat(),
            "system_status": "operational"
        }
        
    except Exception as e:
        logger.error(f"세션 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="세션 통계 조회에 실패했습니다.")

async def _generate_work_details_with_llm(recommendation, user_message: str) -> dict:
    """
    LLM을 사용하여 작업상세 생성
    
    Args:
        recommendation: 선택된 추천 항목
        user_message: 사용자 원본 메시지
        
    Returns:
        생성된 작업명과 상세 딕셔너리
        
    사용처:
    - generate_work_details()에서 호출
    - logic/recommender.py의 _generate_work_details()와 유사한 로직
    
    담당자 수정 가이드:
    - 프롬프트 수정으로 생성 품질 향상 가능
    - temperature 조정으로 창의성 제어 가능
    - 특정 설비유형별 맞춤 프롬프트 사용 가능
    """
    try:
        # LLM 프롬프트 생성
        prompt = _create_work_details_prompt(recommendation, user_message)
        
        # LLM 호출
        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "당신은 설비관리 시스템의 작업명과 상세 생성 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 적당한 창의성
            max_tokens=400
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 응답 파싱
        work_details = _parse_work_details_response(result_text)
        return work_details
        
    except Exception as e:
        logger.error(f"LLM 작업상세 생성 오류: {e}")
        return {}

def _create_work_details_prompt(recommendation, user_message: str) -> str:
    """
    작업상세 생성용 LLM 프롬프트 생성
    
    Args:
        recommendation: 선택된 추천 항목
        user_message: 사용자 원본 메시지
        
    Returns:
        LLM 프롬프트 문자열
        
    담당자 수정 가이드:
    - 작업명/상세 길이 제한 조정 가능
    - 특정 설비유형별 맞춤 지침 추가 가능
    - 예시는 실제 사용 사례를 반영하여 업데이트
    - 안전 지침이나 규정 준수 요구사항 추가 가능
    """
    
    return f"""
다음 설비관리 작업에 대한 작업명과 상세를 생성해주세요.

**설비 정보**:
- 공정: {recommendation.process}
- 위치: {recommendation.location}
- 설비유형: {recommendation.equipType}
- 현상코드: {recommendation.statusCode}
- 우선순위: {recommendation.priority}

**사용자 원본 입력**: {user_message}

**생성 요구사항**:
1. 작업명: 20자 이내의 간결하고 명확한 제목
2. 작업상세: 100자 이내의 구체적인 작업 내용
3. 설비유형과 현상에 맞는 전문적인 용어 사용
4. 안전과 효율성을 고려한 작업 방법 제시
5. 사용자 입력의 의도를 반영

**응답 형식**:
```json
{{
    "work_title": "생성된 작업명",
    "work_details": "생성된 작업상세"
}}
```

**예시**:
- 설비: Pressure Vessel, 현상: 고장
- 작업명: "압력용기 고장 점검 및 수리"
- 작업상세: "압력용기 내부 점검 후 고장 부위 확인 및 수리 작업 수행"

- 설비: Motor Operated Valve, 현상: 누설
- 작업명: "모터밸브 누설 점검"
- 작업상세: "밸브 패킹 및 시트 점검 후 필요시 교체 작업 수행"

**주의사항**:
- 안전 작업 절차 준수
- 환경 보호 고려
- 작업 효율성 극대화
"""

def _parse_work_details_response(response_text: str) -> dict:
    """
    작업상세 생성 응답 파싱
    
    Args:
        response_text: LLM 응답 텍스트
        
    Returns:
        파싱된 작업명과 상세 딕셔너리
        
    담당자 수정 가이드:
    - JSON 파싱 실패 시 폴백 로직으로 응답에서 정보 추출
    - 응답 형식이 변경되면 이 메서드 수정 필요
    """
    try:
        import re
        import json
        
        # JSON 부분 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            # JSON 블록이 없는 경우 전체 텍스트를 JSON으로 파싱 시도
            data = json.loads(response_text)
        
        return {
            'work_title': data.get('work_title', ''),
            'work_details': data.get('work_details', '')
        }
        
    except Exception as e:
        logger.error(f"작업상세 응답 파싱 오류: {e}")
        return {}

def _generate_work_order_itemno() -> str:
    """
    작업요청 번호 생성
    
    Returns:
        생성된 작업요청 번호
        
    생성 규칙:
    - 현재: UUID 기반 (개발/테스트용)
    - 실제 운영: 외부 시스템 규칙에 따라 생성
    
    담당자 수정 가이드:
    - 실제 운영 환경에서는 외부 시스템 연동 필요
    - 번호 생성 규칙 변경 가능
    - 중복 방지 로직 추가 필요
    """
    # 개발/테스트용: UUID 기반 번호 생성
    # 실제 운영에서는 외부 시스템에서 생성
    return f"WO{uuid.uuid4().hex[:8].upper()}"

def _create_completion_message(work_order: WorkOrder) -> str:
    """
    작업요청 완성 메시지 생성
    
    Args:
        work_order: 완성된 작업요청
        
    Returns:
        사용자에게 보여질 완성 메시지
        
    담당자 수정 가이드:
    - 메시지 형식 개선 가능
    - 다음 단계 안내 추가 가능
    - 개인화된 메시지 생성 가능
    """
    
    message = f"✅ 작업요청이 성공적으로 완성되었습니다!\n\n"
    message += f"**작업요청 번호**: {work_order.itemno}\n"
    message += f"**작업명**: {work_order.work_title}\n"
    message += f"**작업상세**: {work_order.work_details}\n\n"
    message += f"**설비 정보**\n"
    message += f"• 공정: {work_order.process}\n"
    message += f"• 위치: {work_order.location}\n"
    message += f"• 설비유형: {work_order.equipType}\n"
    message += f"• 현상코드: {work_order.statusCode}\n"
    message += f"• 우선순위: {work_order.priority}\n\n"
    message += f"작업요청이 시스템에 등록되었습니다. 담당자가 검토 후 작업을 진행할 예정입니다."
    
    return message 