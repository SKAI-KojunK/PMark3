"""
PMark1 AI Assistant - 추천 엔진

이 파일은 파싱된 사용자 입력을 기반으로 유사한 작업을 검색하고 추천하는 엔진입니다.
데이터베이스에서 유사한 알림 데이터를 찾아 우선순위와 유사도 점수를 계산하여 추천 목록을 생성합니다.

주요 담당자: AI/ML 엔지니어, 백엔드 개발자
수정 시 주의사항:
- 추천 알고리즘은 비즈니스 로직에 따라 조정 가능
- 유사도 점수 계산 로직은 database.py와 연동
- LLM을 활용한 작업명/상세 생성 기능 포함
"""

from openai import OpenAI
from typing import List, Dict, Optional
from ..models import ParsedInput, Recommendation
from ..database import db_manager
from ..config import Config
import logging

class RecommendationEngine:
    """
    추천 엔진 클래스
    
    사용처:
    - chat.py: POST /api/v1/chat에서 추천 목록 생성
    - work_details.py: 선택된 추천 항목의 작업상세 생성
    
    연계 파일:
    - models.py: ParsedInput, Recommendation 모델 사용
    - database.py: search_similar_notifications() 호출
    - logic/normalizer.py: 이미 정규화된 입력 사용
    
    담당자 수정 가이드:
    - 추천 알고리즘 개선 시 get_recommendations() 메서드 수정
    - 유사도 점수 임계값 조정으로 추천 품질 제어
    - 새로운 추천 기준 추가 가능
    """
    
    def __init__(self):
        """
        추천 엔진 초기화
        
        설정:
        - OpenAI 클라이언트 초기화
        - 로깅 설정
        """
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        self.logger = logging.getLogger(__name__)
    
    def get_recommendations(self, parsed_input: ParsedInput, limit: int = 5) -> List[Recommendation]:
        """
        파싱된 입력을 기반으로 추천 목록 생성
        
        Args:
            parsed_input: 파싱된 사용자 입력
            limit: 반환할 최대 추천 수
            
        Returns:
            추천 항목 리스트 (유사도 점수 순으로 정렬)
            
        사용처:
        - chat.py: chat_endpoint()에서 추천 목록 생성
        - frontend: 사용자에게 추천 항목 표시
        
        연계 파일:
        - models.py: ParsedInput 입력, Recommendation 출력
        - database.py: search_similar_notifications() 호출
        - logic/normalizer.py: 이미 정규화된 입력 사용
        
        예시:
        - ParsedInput(location="No.1 PE", equipment_type="Pressure Vessel", status_code="고장")
        - → [Recommendation(itemno="12345", score=0.95), ...]
        
        담당자 수정 가이드:
        - 추천 알고리즘 개선 시 검색 조건 조정
        - 유사도 점수 임계값 조정으로 추천 품질 제어
        - 새로운 추천 기준 추가 가능
        """
        try:
            # 추천 조건 확인: 위치, 설비유형, 현상코드가 모두 있어야 추천
            if not all([parsed_input.location, parsed_input.equipment_type, parsed_input.status_code]):
                self.logger.info("추천 조건 미충족: 위치, 설비유형, 현상코드가 모두 필요합니다.")
                return []
            
            # 데이터베이스에서 유사한 알림 검색
            similar_notifications = db_manager.search_similar_notifications(
                equip_type=parsed_input.equipment_type,
                location=parsed_input.location,
                status_code=parsed_input.status_code,
                priority=parsed_input.priority,
                limit=limit * 2  # 더 많은 결과를 가져와서 필터링
            )
            
            if not similar_notifications:
                self.logger.warning("유사한 알림을 찾을 수 없습니다.")
                return []
            
            # 유사도 점수 계산 및 추천 항목 생성 (LLM 호출 최소화)
            recommendations = []
            for notification in similar_notifications:
                # 간단한 문자열 매칭 기반 유사도 점수 계산 (LLM 호출 없음)
                score = self._calculate_simple_similarity_score(
                    parsed_input, notification
                )
                
                # 유사도 점수가 임계값 이상인 경우만 추천 (임계값을 낮춰서 더 많은 추천 제공)
                if score > 0.2:  # 0.3에서 0.2로 낮춤
                    recommendation = Recommendation(
                        itemno=notification['itemno'],
                        process=notification['process'],
                        location=notification['location'],
                        cost_center=notification.get('cost_center'),
                        equipType=notification['equipType'],
                        statusCode=notification['statusCode'],
                        priority=notification['priority'],
                        score=score,
                        work_title=notification.get('work_title'),
                        work_details=notification.get('work_details')
                    )
                    recommendations.append(recommendation)
            
            # 유사도 점수 순으로 정렬
            recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # 요구사항에 따른 결과 처리
            total_count = len(recommendations)
            self.logger.info(f"총 {total_count}개의 추천 항목 발견")
            
            if total_count == 0:
                return []
            elif 1 <= total_count <= 5:
                # 1-5개: 해당 값만 반환
                top_recommendations = recommendations
                self.logger.info(f"1-5개 범위: {total_count}개 모두 반환")
            elif 6 <= total_count <= 15:
                # 6-15개: 5개씩 묶어서 순차적으로 반환 (첫 번째 배치)
                top_recommendations = recommendations[:5]
                self.logger.info(f"6-15개 범위: 첫 번째 배치 5개 반환 (총 {total_count}개 중)")
            else:
                # 15개 이상: 아이템 넘버 입력 요청을 위해 특별한 처리
                # 일단 상위 15개로 제한하되, 추가 정보를 포함
                top_recommendations = recommendations[:15]
                self.logger.warning(f"15개 이상 ({total_count}개): 아이템 넘버 입력 요청 필요")
            
            # LLM을 사용하여 작업명과 상세 생성 (없는 경우)
            for rec in top_recommendations:
                if not rec.work_title or not rec.work_details:
                    work_info = self._generate_work_details(rec, parsed_input)
                    if work_info:
                        rec.work_title = work_info.get('work_title', rec.work_title)
                        rec.work_details = work_info.get('work_details', rec.work_details)
            
            self.logger.info(f"추천 목록 생성 완료: {len(top_recommendations)} 건")
            return top_recommendations
            
        except Exception as e:
            self.logger.error(f"추천 생성 오류: {e}")
            return []
    
    def _generate_work_details(self, recommendation: Recommendation, parsed_input: ParsedInput) -> Optional[Dict]:
        """
        LLM을 사용하여 작업명과 상세 생성
        
        Args:
            recommendation: 추천 항목
            parsed_input: 원본 파싱된 입력
            
        Returns:
            생성된 작업명과 상세 (없으면 None)
            
        사용처:
        - get_recommendations()에서 작업명/상세가 없는 추천 항목에 대해 호출
        - work_details.py: generate_work_details()에서도 유사한 로직 사용
        
        담당자 수정 가이드:
        - 프롬프트 수정으로 생성 품질 향상 가능
        - 작업명/상세 길이 제한 조정 가능
        - 특정 설비유형별 맞춤 프롬프트 사용 가능
        """
        try:
            prompt = self._create_work_details_prompt(recommendation, parsed_input)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 설비관리 시스템의 작업명과 상세 생성 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 적당한 창의성
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 응답 파싱
            work_info = self._parse_work_details_response(result_text)
            return work_info
            
        except Exception as e:
            self.logger.error(f"작업상세 생성 오류: {e}")
            return None
    
    def _create_work_details_prompt(self, recommendation: Recommendation, parsed_input: ParsedInput) -> str:
        """
        작업상세 생성용 LLM 프롬프트 생성
        
        Args:
            recommendation: 추천 항목
            parsed_input: 원본 파싱된 입력
            
        Returns:
            LLM 프롬프트 문자열
            
        담당자 수정 가이드:
        - 작업명/상세 길이 제한 조정 가능
        - 특정 설비유형별 맞춤 지침 추가 가능
        - 예시는 실제 사용 사례를 반영하여 업데이트
        """
        
        return f"""
다음 설비관리 작업에 대한 작업명과 상세를 생성해주세요.

**설비 정보**:
- 공정: {recommendation.cost_center if recommendation.cost_center else recommendation.process}
- 위치: {recommendation.location}
- 설비유형: {recommendation.equipType}
- 현상코드: {recommendation.statusCode}
- 우선순위: {recommendation.priority}

**사용자 원본 입력**: {parsed_input}

**생성 요구사항**:
1. 작업명: 20자 이내의 간결하고 명확한 제목
2. 작업상세: 100자 이내의 구체적인 작업 내용
3. 설비유형과 현상에 맞는 전문적인 용어 사용
4. 안전과 효율성을 고려한 작업 방법 제시

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
"""
    
    def _parse_work_details_response(self, response_text: str) -> Optional[Dict]:
        """
        작업상세 생성 응답 파싱
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            파싱된 작업명과 상세 (없으면 None)
            
        담당자 수정 가이드:
        - JSON 파싱 실패 시 폴백 로직으로 응답에서 정보 추출
        - 응답 형식이 변경되면 이 메서드 수정 필요
        """
        try:
            # JSON 부분 추출
            import re
            import json
            
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
            self.logger.error(f"작업상세 응답 파싱 오류: {e}")
            return None
    
    def get_recommendation_by_itemno(self, itemno: str) -> Optional[Recommendation]:
        """
        ITEMNO로 특정 추천 항목 조회
        
        Args:
            itemno: 추천 항목 번호
            
        Returns:
            추천 항목 (없으면 None)
            
        사용처:
        - work_details.py: 선택된 추천 항목의 상세 정보 조회
        - chat.py: 특정 추천 항목 확인
        
        담당자 수정 가이드:
        - 캐싱을 통한 성능 향상 가능
        - 관련 추천 항목도 함께 조회 가능
        """
        try:
            notification = db_manager.get_notification_by_itemno(itemno)
            if notification:
                return Recommendation(
                    itemno=notification['itemno'],
                    process=notification['process'],
                    location=notification['location'],
                    cost_center=notification.get('cost_center'),
                    equipType=notification['equipType'],
                    statusCode=notification['statusCode'],
                    priority=notification['priority'],
                    score=1.0,  # 정확한 매칭
                    work_title=notification.get('work_title'),
                    work_details=notification.get('work_details')
                )
            return None
            
        except Exception as e:
            self.logger.error(f"ITEMNO 추천 항목 조회 오류: {e}")
            return None
    
    def filter_recommendations_by_priority(self, recommendations: List[Recommendation], priority: str) -> List[Recommendation]:
        """
        우선순위별로 추천 항목 필터링
        
        Args:
            recommendations: 추천 항목 리스트
            priority: 필터링할 우선순위
            
        Returns:
            필터링된 추천 항목 리스트
            
        사용처:
        - frontend: 우선순위별 필터링 기능
        - chat.py: 특정 우선순위 추천만 제공
        
        담당자 수정 가이드:
        - 복합 필터링 조건 추가 가능
        - 정렬 기준 추가 가능
        """
        return [rec for rec in recommendations if rec.priority == priority]
    
    def _calculate_simple_similarity_score(self, parsed_input: ParsedInput, notification: Dict) -> float:
        """
        개선된 유사도 점수 계산 (LLM 호출 없음)
        
        Args:
            parsed_input: 파싱된 입력 데이터
            notification: 데이터베이스 알림 데이터
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
            
        담당자 수정 가이드:
        - 매칭 로직 개선으로 정확도 향상 가능
        - 가중치 조정으로 특정 필드 중요도 변경 가능
        - 새로운 매칭 기준 추가 가능
        """
        score = 0.0
        total_weight = 0.0
        
        # 설비유형 매칭 (가중치: 0.35)
        if parsed_input.equipment_type and notification['equipType']:
            equip_match = self._calculate_enhanced_string_similarity(
                parsed_input.equipment_type.lower(), 
                notification['equipType'].lower()
            )
            score += equip_match * 0.35
            total_weight += 0.35
        
        # 위치/공정명 매칭 (가중치: 0.35)
        # 사용자가 "공정명"으로 입력한 경우 DB의 "Location" 컬럼과 매칭
        if parsed_input.location and notification['location']:
            location_match = self._calculate_enhanced_string_similarity(
                parsed_input.location.lower(), 
                notification['location'].lower()
            )
            score += location_match * 0.35
            total_weight += 0.35
        
        # 현상코드 매칭 (가중치: 0.2)
        if parsed_input.status_code and notification['statusCode']:
            status_match = self._calculate_enhanced_string_similarity(
                parsed_input.status_code.lower(), 
                notification['statusCode'].lower()
            )
            score += status_match * 0.2
            total_weight += 0.2
        
        # 우선순위 매칭 (가중치: 0.1)
        if parsed_input.priority and notification['priority']:
            priority_match = self._calculate_enhanced_string_similarity(
                parsed_input.priority.lower(), 
                notification['priority'].lower()
            )
            score += priority_match * 0.1
            total_weight += 0.1
        
        # 가중 평균 계산
        final_score = score / total_weight if total_weight > 0 else 0.0
        
        # 보너스 점수: 모든 필드가 매칭되는 경우
        if (parsed_input.equipment_type and parsed_input.location and 
            parsed_input.status_code and parsed_input.priority):
            if (equip_match > 0.8 and location_match > 0.8 and 
                status_match > 0.8 and priority_match > 0.8):
                final_score = min(final_score + 0.1, 1.0)  # 최대 0.1점 보너스
        
        return final_score
    
    def _calculate_enhanced_string_similarity(self, str1: str, str2: str) -> float:
        """
        개선된 문자열 유사도 계산
        
        Args:
            str1: 첫 번째 문자열
            str2: 두 번째 문자열
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        if not str1 or not str2:
            return 0.0
        
        # 정확한 매칭
        if str1 == str2:
            return 1.0
        
        # 부분 매칭 (포함 관계)
        if str1 in str2 or str2 in str1:
            # 포함된 문자열의 길이 비율에 따라 점수 조정
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            ratio = shorter / longer
            return 0.7 + (ratio * 0.2)  # 0.7 ~ 0.9 범위
        
        # 공통 단어 수 계산
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        word_similarity = len(common_words) / len(total_words) if total_words else 0.0
        
        # 문자 단위 유사도 계산 (Levenshtein 거리 기반)
        char_similarity = self._calculate_character_similarity(str1, str2)
        
        # 단어 유사도와 문자 유사도의 가중 평균
        return (word_similarity * 0.7) + (char_similarity * 0.3)
    
    def _calculate_character_similarity(self, str1: str, str2: str) -> float:
        """
        문자 단위 유사도 계산 (간단한 Levenshtein 거리 기반)
        
        Args:
            str1: 첫 번째 문자열
            str2: 두 번째 문자열
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        if not str1 or not str2:
            return 0.0
        
        # 간단한 편집 거리 계산
        len1, len2 = len(str1), len(str2)
        
        # 동적 프로그래밍 테이블
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # 초기화
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        
        # 편집 거리 계산
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
        
        # 유사도 점수 계산 (편집 거리를 유사도로 변환)
        max_len = max(len1, len2)
        if max_len == 0:
            return 1.0
        
        distance = dp[len1][len2]
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def get_recommendation_statistics(self, recommendations: List[Recommendation]) -> Dict:
        """
        추천 항목 통계 정보 생성
        
        Args:
            recommendations: 추천 항목 리스트
            
        Returns:
            통계 정보 딕셔너리
            
        사용처:
        - frontend: 추천 통계 표시
        - 분석: 추천 품질 평가
        
        담당자 수정 가이드:
        - 새로운 통계 항목 추가 가능
        - 시각화용 데이터 형식 조정 가능
        """
        if not recommendations:
            return {}
        
        priorities = {}
        equip_types = {}
        avg_score = sum(rec.score for rec in recommendations) / len(recommendations)
        
        for rec in recommendations:
            # 우선순위별 카운트
            priorities[rec.priority] = priorities.get(rec.priority, 0) + 1
            
            # 설비유형별 카운트
            equip_types[rec.equipType] = equip_types.get(rec.equipType, 0) + 1
        
        return {
            'total_count': len(recommendations),
            'average_score': round(avg_score, 3),
            'priority_distribution': priorities,
            'equipment_type_distribution': equip_types,
            'top_score': max(rec.score for rec in recommendations),
            'lowest_score': min(rec.score for rec in recommendations)
        }

# 전역 추천 엔진 인스턴스
# 다른 모듈에서 import하여 사용
recommendation_engine = RecommendationEngine() 