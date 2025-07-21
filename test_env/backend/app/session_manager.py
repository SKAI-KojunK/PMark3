"""
PMark2.5 AI Assistant - 세션 상태 관리자

이 파일은 멀티턴 대화에서 세션 상태와 누적된 컨텍스트를 관리합니다.
각 사용자 세션별로 단서 항목들을 누적하고, 세션 생명주기를 관리합니다.

주요 담당자: 백엔드 개발자, AI/ML 엔지니어
수정 시 주의사항:
- 메모리 기반 저장이므로 서버 재시작 시 세션 초기화
- 향후 Redis 등 영구 저장소로 확장 가능
- 세션 타임아웃 관리로 메모리 누수 방지 필요
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from .models import SessionState, AccumulatedClues, ParsedInput, ChatMessage
import logging

class SessionManager:
    """
    세션 상태 관리 클래스
    
    사용처:
    - chat.py: 세션 기반 컨텍스트 유지
    - parser.py: 누적된 단서 항목 활용
    
    담당자 수정 가이드:
    - _sessions는 메모리 기반 저장 (향후 DB 확장 가능)
    - SESSION_TIMEOUT으로 오래된 세션 정리
    - 세션 상태별 다른 처리 로직 추가 가능
    """
    
    def __init__(self):
        """
        세션 매니저 초기화
        
        설정:
        - 메모리 기반 세션 저장소
        - 세션 타임아웃 설정 (30분)
        - 로깅 설정
        """
        self._sessions: Dict[str, SessionState] = {}
        self.SESSION_TIMEOUT = timedelta(minutes=30)  # 30분 타임아웃
        self.logger = logging.getLogger(__name__)
        
    def create_session(self) -> str:
        """
        새로운 세션 생성
        
        Returns:
            생성된 세션 ID
            
        사용처:
        - 첫 대화 시작 시
        - 명시적 새 세션 요청 시
        - 세션 타임아웃 후 재시작 시
        """
        session_id = str(uuid.uuid4())
        
        session_state = SessionState(
            session_id=session_id,
            accumulated_clues=AccumulatedClues(),
            session_status="collecting_info",
            created_at=datetime.now(),
            last_updated=datetime.now(),
            turn_count=0
        )
        
        self._sessions[session_id] = session_state
        self.logger.info(f"새 세션 생성: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 상태 객체 (없으면 None)
            
        주의사항:
        - 타임아웃된 세션은 자동 삭제
        - 존재하지 않는 세션은 None 반환
        """
        if session_id not in self._sessions:
            return None
            
        session = self._sessions[session_id]
        
        # 타임아웃 체크
        if datetime.now() - session.last_updated > self.SESSION_TIMEOUT:
            self.logger.info(f"세션 타임아웃으로 삭제: {session_id}")
            del self._sessions[session_id]
            return None
            
        return session
    
    def update_session(self, session_id: str, parsed_input: ParsedInput, 
                      conversation_history: List[ChatMessage] = None) -> SessionState:
        """
        세션 상태 업데이트
        
        Args:
            session_id: 세션 ID
            parsed_input: 새로 파싱된 입력
            conversation_history: 대화 히스토리 (선택사항)
            
        Returns:
            업데이트된 세션 상태
            
        처리 과정:
        1. 기존 누적 단서와 새 입력 병합
        2. 세션 상태 업데이트 (collecting_info/recommending)
        3. 턴 카운트 증가
        4. 마지막 업데이트 시간 갱신
        """
        session = self.get_session(session_id)
        if not session:
            # 세션이 없으면 새로 생성
            self.logger.info(f"세션 없음. 새 세션 생성: {session_id}")
            session_id = self.create_session()
            session = self._sessions[session_id]
        
        # 기존 누적 단서 로그
        self.logger.info(f"기존 누적 단서 - 위치: {session.accumulated_clues.location}, 설비: {session.accumulated_clues.equipment_type}, 현상: {session.accumulated_clues.status_code}")
        
        # 새 파싱 입력 로그
        self.logger.info(f"새 파싱 입력 - 위치: {parsed_input.location}, 설비: {parsed_input.equipment_type}, 현상: {parsed_input.status_code}")
        
        # 누적 단서와 새 입력 병합
        merged_clues = session.accumulated_clues.merge_with(parsed_input)
        
        # 병합 결과 로그
        self.logger.info(f"병합 결과 - 위치: {merged_clues.location}, 설비: {merged_clues.equipment_type}, 현상: {merged_clues.status_code}")
        
        # 세션 상태 결정
        new_status = self._determine_session_status(merged_clues, parsed_input)
        
        # 세션 업데이트
        session.accumulated_clues = merged_clues
        session.session_status = new_status
        session.turn_count += 1
        session.last_updated = datetime.now()
        
        self.logger.info(f"세션 업데이트 완료: {session_id}, 상태: {new_status}, 턴: {session.turn_count}")
        
        return session
    
    def _determine_session_status(self, clues: AccumulatedClues, parsed_input: ParsedInput) -> str:
        """
        누적된 단서를 기반으로 세션 상태 결정
        
        Args:
            clues: 누적된 단서 항목들
            parsed_input: 현재 입력
            
        Returns:
            세션 상태 ("collecting_info", "recommending", "finalizing")
            
        상태 결정 로직:
        - collecting_info: 기본 정보 수집 중
        - recommending: 충분한 정보로 추천 가능
        - finalizing: 작업 완료 단계 (ITEMNO 선택 등)
        """
        # ITEMNO가 있으면 완료 단계
        if parsed_input.scenario == "S2" or clues.itemno:
            return "finalizing"
            
        # 충분한 정보가 있으면 추천 단계
        if clues.has_sufficient_info():
            return "recommending"
            
        # 기본값: 정보 수집 단계
        return "collecting_info"
    
    def finalize_session(self, session_id: str) -> bool:
        """
        세션 완료 및 종료
        
        Args:
            session_id: 세션 ID
            
        Returns:
            성공 여부
            
        사용처:
        - 작업요청 완료 후
        - 사용자가 명시적으로 종료 요청 시
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.session_status = "completed"
            session.last_updated = datetime.now()
            
            self.logger.info(f"세션 완료: {session_id}")
            return True
        return False
    
    def clear_session(self, session_id: str) -> bool:
        """
        세션 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            삭제 성공 여부
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            self.logger.info(f"세션 삭제: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """
        만료된 세션들 정리
        
        정리 대상:
        - 타임아웃된 세션들
        - 완료 후 5분 경과한 세션들
        
        사용처:
        - 주기적 호출 (cron job 등)
        - 메모리 사용량 관리
        """
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            # 일반 타임아웃 체크
            if current_time - session.last_updated > self.SESSION_TIMEOUT:
                expired_sessions.append(session_id)
                continue
                
            # 완료된 세션 중 5분 경과한 것들
            if (session.session_status == "completed" and 
                current_time - session.last_updated > timedelta(minutes=5)):
                expired_sessions.append(session_id)
        
        # 만료된 세션들 삭제
        for session_id in expired_sessions:
            del self._sessions[session_id]
            self.logger.info(f"만료된 세션 삭제: {session_id}")
            
        if expired_sessions:
            self.logger.info(f"총 {len(expired_sessions)}개 세션 정리 완료")
    
    def get_session_stats(self) -> Dict:
        """
        세션 통계 정보 반환
        
        Returns:
            세션 통계 딕셔너리
            
        사용처:
        - 시스템 모니터링
        - 성능 분석
        """
        stats = {
            "total_sessions": len(self._sessions),
            "status_breakdown": {},
            "avg_turn_count": 0
        }
        
        if self._sessions:
            # 상태별 세션 수
            for session in self._sessions.values():
                status = session.session_status
                stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
            
            # 평균 턴 수
            total_turns = sum(session.turn_count for session in self._sessions.values())
            stats["avg_turn_count"] = total_turns / len(self._sessions)
        
        return stats
    
    def extract_context_from_history(self, conversation_history: List[ChatMessage]) -> AccumulatedClues:
        """
        대화 히스토리에서 컨텍스트 추출 (백업 방법)
        
        Args:
            conversation_history: 대화 히스토리
            
        Returns:
            추출된 누적 단서들
            
        사용처:
        - 세션이 없을 때 히스토리에서 컨텍스트 복원
        - 세션 데이터 손실 시 백업 복구
        
        담당자 수정 가이드:
        - 현재는 기본 구현만 제공
        - 향후 NLP 기반 컨텍스트 추출 로직 추가 가능
        """
        # 현재는 기본 빈 객체 반환
        # 향후 대화 히스토리 분석을 통한 컨텍스트 추출 로직 구현 예정
        return AccumulatedClues()

# 전역 세션 매니저 인스턴스
session_manager = SessionManager() 