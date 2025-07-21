"""
PMark3 지능형 추천 엔진

=== 모듈 개요 ===
파싱된 사용자 입력을 기반으로 유사한 작업을 검색하고 우선순위별로 추천하는 핵심 엔진입니다.
다중 유사도 계산 알고리즘과 LLM 기반 작업상세 생성으로 정확하고 유용한 추천을 제공합니다.

=== Production 전환 주요 포인트 ===
🔄 벡터 검색 통합: 문자열 매칭 → 의미적 유사도 검색으로 진화
🤖 협업 필터링: 사용자 행동 데이터 기반 개인화 추천 추가
📊 실시간 학습: 사용자 피드백을 통한 추천 모델 지속 개선
🚀 성능 최적화: 캐싱, 배치 처리, 비동기 처리로 응답 속도 향상

=== 현재 vs Production 추천 방식 비교 ===
📋 현재 방식:
- 키워드 기반 검색 (database.py 활용)
- 문자열 유사도 계산 (Levenshtein 거리)
- 가중치 기반 점수 산정 (equipment: 35%, location: 35%, status: 20%, priority: 10%)
- LLM 기반 작업상세 생성

🚀 Production 방식:
- 하이브리드 검색: 키워드 + 벡터 + 협업 필터링
- 의미적 유사도: 임베딩 기반 코사인 유사도
- 동적 가중치: 사용자별/상황별 적응적 가중치
- 실시간 개인화: 사용자 히스토리 기반 추천

=== 연계 시스템 상세 ===
⬅️ 입력단:
- agents/parser.py: ParsedInput 객체 → get_recommendations()
- api/chat.py: 사용자 세션 → 추천 목록 생성
- session_manager.py: 사용자 히스토리 → 개인화 추천

➡️ 출력단:
- database.py: search_similar_notifications() → 후보 데이터 수집
- api/work_details.py: 선택된 추천 → 상세 작업 정보 생성
- frontend: 추천 목록 → 사용자 인터페이스 표시

=== AI 연구원 실험 포인트 ===
1. 유사도 알고리즘 개선: notebooks/03_recommender_experiment.ipynb 활용
2. 가중치 최적화: 설비별/상황별 최적 가중치 탐색
3. 벡터 검색 통합: SentenceTransformer + FAISS 성능 비교
4. 협업 필터링: Matrix Factorization vs Deep Learning 기반 추천

=== 개발팀 구현 가이드 ===
🏗️ 벡터 기반 추천 아키텍처:
```python
class VectorRecommendationEngine:
    def __init__(self, vector_db, embedding_model):
        self.vector_db = vector_db
        self.embedding_model = embedding_model
        self.traditional_engine = RecommendationEngine()
    
    async def get_hybrid_recommendations(self, parsed_input, limit=5):
        # 1. 벡터 검색 (의미적 유사도)
        vector_results = await self.vector_search(parsed_input)
        
        # 2. 전통적 키워드 검색
        keyword_results = self.traditional_engine.get_recommendations(parsed_input)
        
        # 3. 결과 융합 및 재순위화
        return await self.merge_and_rerank(vector_results, keyword_results)
```

📈 성능 모니터링 지표:
- 추천 정확도: Precision@K, Recall@K, F1-Score
- 사용자 만족도: 클릭률, 선택률, 완료율
- 시스템 성능: 평균 응답 시간, 처리량, 메모리 사용량
- 개인화 효과: 개인화 vs 일반 추천 성능 비교
"""

from openai import OpenAI
import pandas as pd
import os
from typing import List, Dict, Optional
from ..models import ParsedInput, Recommendation
from ..database import db_manager
from ..config import Config
import logging

class RecommendationEngine:
    """
    지능형 추천 엔진 핵심 클래스 (현재 프로토타입)
    
    === 현재 아키텍처에서의 역할 ===
    🎯 시나리오별 추천: S1(자연어) vs S2(ITEMNO) 분기 처리
    🔍 유사도 계산: 다중 필드 가중치 기반 점수 산정
    📊 우선순위 처리: 긴급/우선/일반 작업 분류 및 추천
    🤖 LLM 연동: 작업명/상세 자동 생성 (누락 시)
    
    === Production 전환 시 변경사항 ===
    🔄 LangGraph 노드화:
    - get_recommendations() → recommendation_node()
    - 시나리오별 분기 → 조건부 엣지 처리
    - 비동기 처리 지원 및 상태 관리
    
    🚀 벡터 검색 통합:
    ```python
    # 현재: 키워드 기반 검색
    similar_notifications = db_manager.search_similar_notifications(
        equip_type=parsed_input.equipment_type,
        location=parsed_input.location,
        status_code=parsed_input.status_code
    )
    
    # Production: 하이브리드 검색
    async def get_hybrid_recommendations(self, parsed_input):
        # 1. 벡터 검색 (의미적 유사도)
        vector_results = await self.vector_search(parsed_input)
        # 2. 키워드 검색 (기존 방식)
        keyword_results = await self.keyword_search(parsed_input)
        # 3. 결과 융합 및 재순위화
        return await self.merge_and_rerank(vector_results, keyword_results)
    ```
    
    📈 개인화 추천:
    - 사용자 히스토리 분석 → 선호도 학습
    - 협업 필터링 → 유사 사용자 기반 추천
    - A/B 테스트 → 추천 알고리즘 성능 비교
    
    === 연계 지점 상세 분석 ===
    ⬅️ 호출하는 모듈:
    - api/chat.py.chat_endpoint() → get_recommendations()
    - api/work_details.py → get_recommendation_by_itemno()
    
    ➡️ 호출되는 모듈:
    - database.py.search_similar_notifications() → 후보 데이터 수집
    - database.py.search_by_itemno() → ITEMNO 기반 검색
    - OpenAI API → 작업상세 자동 생성
    
    === AI 연구원 실험 가이드 ===
    📝 유사도 개선 실험:
    - notebooks/03_recommender_experiment.ipynb 활용
    - 가중치 조정: equipment(35%) vs location(35%) vs status(20%) vs priority(10%)
    - 새로운 유사도 메트릭: TF-IDF, BM25, 의미적 유사도
    
    🔬 추천 품질 평가:
    - Precision@K, Recall@K 계산
    - 사용자 피드백 수집 및 분석
    - 다양성 지표 (Diversity, Coverage) 측정
    
    === 개발팀 구현 참고 ===
    🏗️ 성능 최적화 포인트:
    - 결과 캐싱: 동일 쿼리 재사용 (TTL: 30분)
    - 배치 처리: 다중 추천 요청 동시 처리
    - 비동기 LLM 호출: 작업상세 생성 병렬화
    
    📊 모니터링 지표:
    - 추천 정확도: 사용자 선택률 (목표: >70%)
    - 응답 시간: 평균 처리 시간 (목표: <500ms)
    - 시스템 안정성: 에러율 (목표: <1%)
    
    🎯 확장성 고려사항:
    - 추천 모델 A/B 테스트 프레임워크
    - 실시간 사용자 피드백 수집
    - 추천 이유 설명 기능 (Explainable AI)
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
        self.noti_history_df = None
        self.itemno_col = None # '작업대상' 컬럼을 저장할 변수
        self.cost_center_col = None
        self._load_noti_history()

    def _find_column(self, df_columns, keywords):
        """데이터프레임 컬럼 목록에서 키워드와 일치하는 컬럼명을 찾습니다."""
        for col in df_columns:
            # 컬럼명을 소문자로 만들고 공백, '.'을 제거하여 비교합니다.
            normalized_col = col.lower().replace(" ", "").replace(".", "")
            if all(keyword.lower() in normalized_col for keyword in keywords):
                return col
        return None

    def _load_noti_history(self):
        """[Noti이력].xlsx 파일을 로드하여 Cost Center 조회를 준비합니다."""
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), *(['..'] * 4)))
            file_path = os.path.join(project_root, '[Noti이력].xlsx')
            
            if not os.path.exists(file_path):
                self.logger.warning(f"Notification history file not found at '{file_path}'. Cost center lookup will be disabled.")
                return

            self.noti_history_df = pd.read_excel(file_path, engine='openpyxl')
            
            # 컬럼명을 유연하게 찾습니다.
            self.itemno_col = self._find_column(self.noti_history_df.columns, ['작업대상'])
            self.cost_center_col = self._find_column(self.noti_history_df.columns, ['cost', 'center'])

            if not self.itemno_col or not self.cost_center_col:
                self.logger.warning(f"Required columns not found in Excel. Itemno Col ('작업대상'): '{self.itemno_col}', Cost Center Col: '{self.cost_center_col}'. Cost center lookup will be disabled.")
                self.noti_history_df = None
                return
            
            self.logger.info(f"Successfully mapped columns -> Itemno: '{self.itemno_col}', Cost Center: '{self.cost_center_col}'")
            
            # 찾은 컬럼의 타입을 문자열로 변환하여 조회 시 타입 에러를 방지합니다.
            self.noti_history_df[self.itemno_col] = self.noti_history_df[self.itemno_col].astype(str)

        except Exception as e:
            self.logger.error(f"Error loading or processing notification history file: {e}")
            self.noti_history_df = None

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
            # 시나리오별 검색 로직 분기
            if parsed_input.scenario == "S2" and parsed_input.itemno:
                # 시나리오 2: ITEMNO 기반 검색
                similar_notifications = db_manager.search_by_itemno(
                    itemno=parsed_input.itemno,
                    limit=limit * 2
                )
            else:
                # 시나리오 1: 자연어 기반 검색
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
                # 시나리오별 유사도 점수 계산
                if parsed_input.scenario == "S2" and parsed_input.itemno:
                    # 시나리오 2: ITEMNO 기반 유사도 점수 계산
                    score = self._calculate_itemno_similarity_score(
                        parsed_input, notification
                    )
                else:
                    # 시나리오 1: 자연어 기반 유사도 점수 계산
                    score = self._calculate_simple_similarity_score(
                        parsed_input, notification
                    )
                
                # 유사도 점수가 임계값 이상인 경우만 추천 (임계값을 낮춰서 더 많은 추천 제공)
                if score > 0.2:  # 0.3에서 0.2로 낮춤
                    # DB에서 가져온 우선순위 사용, 없으면 기본값 설정
                    db_priority = notification.get('priority')
                    final_priority = db_priority if db_priority else '일반작업'
                    
                    # Cost Center 조회
                    cost_center = self._get_cost_center(notification.get('itemno'))
                    
                    # None 값들을 기본값으로 처리 (더 안전한 처리)
                    recommendation = Recommendation(
                        itemno=notification.get('itemno') or '',
                        process=cost_center or notification.get('process') or '미확인',
                        location=notification.get('location') or '',
                        equipType=notification.get('equipType') or '미확인',
                        statusCode=notification.get('statusCode') or '미확인',
                        priority=final_priority,
                        score=score,
                        work_title=notification.get('work_title') or '',
                        work_details=notification.get('work_details') or ''
                    )
                    recommendations.append(recommendation)
            
            # 유사도 점수 순으로 정렬
            recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # 상위 추천 항목만 반환
            top_recommendations = recommendations[:limit]
            
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
            
    def _get_cost_center(self, itemno: str) -> Optional[str]:
        """주어진 itemno에 해당하는 Cost Center를 조회합니다."""
        if self.noti_history_df is None or not itemno or not self.itemno_col or not self.cost_center_col:
            return None
        
        try:
            # '작업대상' 컬럼(itemno_col)을 기준으로 조회합니다.
            match = self.noti_history_df[self.noti_history_df[self.itemno_col] == itemno]
            if not match.empty:
                cost_center = match.iloc[0][self.cost_center_col]
                return str(cost_center) if pd.notna(cost_center) else None
        except Exception as e:
            self.logger.error(f"Error during cost center lookup for itemno {itemno}: {e}")
        
        return None

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
- 공정: {recommendation.process}
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
        if not priority:
            return recommendations
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
        
        # 우선순위 매칭 (가중치: 0.1) - 선택적 항목
        if parsed_input.priority and notification.get('priority'):
            priority_match = self._calculate_enhanced_string_similarity(
                parsed_input.priority.lower(), 
                notification['priority'].lower()
            )
            score += priority_match * 0.1
            total_weight += 0.1
        
        # 가중 평균 계산
        final_score = score / total_weight if total_weight > 0 else 0.0
        
        # 보너스 점수: 핵심 필드가 매칭되는 경우 (우선순위는 선택사항)
        if (parsed_input.equipment_type and parsed_input.location and 
            parsed_input.status_code):
            if (equip_match > 0.8 and location_match > 0.8 and 
                status_match > 0.8):
                final_score = min(final_score + 0.1, 1.0)  # 최대 0.1점 보너스
        
        return final_score
    
    def _calculate_itemno_similarity_score(self, parsed_input: ParsedInput, notification: Dict) -> float:
        """
        시나리오 2용 ITEMNO 기반 유사도 점수 계산
        
        Args:
            parsed_input: 파싱된 입력 데이터 (itemno 포함)
            notification: 데이터베이스 알림 데이터
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
            
        담당자 수정 가이드:
        - ITEMNO 매칭에 높은 가중치 부여
        - 현상코드와 우선순위는 보조적 매칭 기준
        """
        score = 0.0
        total_weight = 0.0
        
        # ITEMNO 매칭 (가중치: 0.7) - 시나리오 2의 핵심
        if parsed_input.itemno and notification.get('itemno'):
            itemno_match = self._calculate_enhanced_string_similarity(
                parsed_input.itemno.lower(), 
                notification['itemno'].lower()
            )
            score += itemno_match * 0.7
            total_weight += 0.7
        
        # 현상코드 매칭 (가중치: 0.2)
        if parsed_input.status_code and notification.get('statusCode'):
            status_match = self._calculate_enhanced_string_similarity(
                parsed_input.status_code.lower(), 
                notification['statusCode'].lower()
            )
            score += status_match * 0.2
            total_weight += 0.2
        
        # 우선순위 매칭 (가중치: 0.1) - 선택적 항목
        if parsed_input.priority and notification.get('priority'):
            priority_match = self._calculate_enhanced_string_similarity(
                parsed_input.priority.lower(), 
                notification['priority'].lower()
            )
            score += priority_match * 0.1
            total_weight += 0.1
        
        # 가중 평균 계산
        final_score = score / total_weight if total_weight > 0 else 0.0
        
        # 보너스 점수: ITEMNO가 정확히 매칭되는 경우
        if (parsed_input.itemno and notification.get('itemno') and 
            parsed_input.itemno.lower() == notification['itemno'].lower()):
            final_score = min(final_score + 0.2, 1.0)  # 최대 0.2점 보너스
        
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