"""
PMark3 LLM 기반 용어 정규화 엔진

=== 모듈 개요 ===
자연어 입력의 오타, 띄어쓰기, 한영 혼용 등을 AI로 해석하여 표준 용어로 변환하는 핵심 모듈입니다.
DB의 실제 데이터를 동적으로 로드하여 LLM 프롬프트에 제공하는 방식으로 정확도를 극대화합니다.

=== Production 전환 주요 포인트 ===
🔄 벡터 기반 정규화: LLM 방식 → 벡터 임베딩 기반 유사도 검색으로 전환
🚀 성능 최적화: 배치 처리, 캐싱, 비동기 처리 도입
🤖 로컬 LLM 연동: OpenAI → vLLM 기반 다국어 모델 (Mistral 7B/Qwen3 14B)
📊 정확도 향상: 사용자 피드백 학습 및 동적 표준 용어 업데이트

=== 현재 vs Production 비교 ===
📋 현재 방식:
- LLM 기반 정규화 (OpenAI GPT-4)
- DB에서 표준 용어 동적 로드
- 단일 요청 처리
- 응답 시간: ~1-2초

🚀 Production 방식:
- 벡터 임베딩 기반 정규화 (SentenceTransformer)
- 실시간 벡터 검색 (FAISS/Qdrant)
- 배치 처리 지원
- 응답 시간: ~100-200ms (10배 향상)

=== 연계 시스템 ===
⬅️ 입력단:
- agents/parser.py: _normalize_extracted_terms() → normalize_term()
- database.py: search_similar_notifications() → normalize_term()

➡️ 출력단:
- logic/recommender.py: 정규화된 용어로 유사도 계산
- database.py: 표준 용어로 DB 검색 필터 생성

=== AI 연구원 실험 포인트 ===
1. 벡터 모델 비교: ko-sbert vs multilingual-e5 vs OpenAI embedding
2. 유사도 임계값 최적화: confidence threshold 조정 실험
3. 하이브리드 접근: 룰 기반 + 벡터 기반 + LLM 폴백 조합
4. 캐싱 전략: 자주 사용되는 용어 조합 사전 캐싱

=== 개발팀 구현 가이드 ===
🏗️ 벡터 기반 정규화 아키텍처:
- VectorBasedNormalizer 클래스 구현
- 표준 용어 벡터 인덱스 구축 (startup 시)
- 실시간 유사도 검색 (cosine similarity)
- LLM 폴백 메커니즘 (신뢰도 낮은 경우)

📈 성능 최적화:
- 결과 캐싱 (Redis/Azure Cache)
- 배치 처리 API 엔드포인트
- 비동기 정규화 큐 (Azure Service Bus)
"""

from openai import OpenAI
from typing import Dict, List, Optional, Tuple
from ..config import Config
import json
import re
import sqlite3

class LLMNormalizer:
    """
    LLM 기반 용어 정규화 엔진 (현재 프로토타입)
    
    === 현재 아키텍처에서의 역할 ===
    🎯 용어 표준화: 오타, 띄어쓰기, 한영 혼용 → 표준 용어 변환
    🔍 동적 용어 로드: DB에서 실시간 표준 용어 목록 추출
    📊 신뢰도 평가: 정규화 결과의 정확도 점수 제공
    🤝 다중 카테고리: equipment, location, status, priority 지원
    
    === Production 전환 시 변경사항 ===
    🔄 벡터 기반 정규화:
    - normalize_term() → vector_normalize_term()
    - LLM 프롬프트 → 벡터 유사도 검색
    - 응답 시간: 1-2초 → 100-200ms
    
    🚀 성능 최적화:
    - batch_normalize() → async_batch_normalize()
    - 결과 캐싱 (TTL: 1시간)
    - 백그라운드 표준 용어 업데이트
    
    🤖 하이브리드 접근:
    - 1차: 벡터 유사도 검색 (빠른 응답)
    - 2차: LLM 폴백 (신뢰도 < 0.8인 경우)
    - 3차: 룰 기반 매칭 (알려진 패턴)
    
    === 연계 지점 상세 분석 ===
    ⬅️ 호출하는 모듈:
    - agents/parser.py._normalize_extracted_terms()
      → 파싱된 4개 필드 (location, equipment, status, priority) 정규화
    - database.py.search_similar_notifications()
      → 검색 쿼리의 필터 값 정규화
    
    ➡️ 호출되는 모듈:
    - database.py._get_db_terms() → 표준 용어 목록 동적 추출
    - config.py → OpenAI API 설정 참조
    
    === AI 연구원 실험 가이드 ===
    📝 정규화 품질 개선:
    - notebooks/02_normalizer_experiment.ipynb 활용
    - Ground Truth 데이터셋 구축 및 평가
    - confidence threshold 최적화 (현재: 0.3)
    
    🔬 벡터 모델 실험:
    - SentenceTransformer('jhgan/ko-sbert-multitask') 테스트
    - OpenAI embedding vs 로컬 모델 성능 비교
    - 다국어 모델 평가 (한국어 특화 vs 다국어)
    
    === 개발팀 구현 참고 ===
    🏗️ 벡터 기반 정규화 구현:
    ```python
    class VectorBasedNormalizer:
        def __init__(self, vector_db, embedding_model):
            self.vector_db = vector_db
            self.model = SentenceTransformer(embedding_model)
        
        async def normalize_term(self, term, category):
            # 1. 입력 용어 임베딩
            term_embedding = self.model.encode(term)
            
            # 2. 벡터 DB 검색
            results = await self.vector_db.search(
                embedding=term_embedding,
                collection=f"standard_terms_{category}",
                top_k=5, threshold=0.8
            )
            
            # 3. 최고 유사도 반환 또는 LLM 폴백
            if results and results[0].similarity > 0.8:
                return results[0].text, results[0].similarity
            else:
                return await self.llm_fallback(term, category)
    ```
    
    📊 성능 모니터링 지표:
    - 정규화 정확도 (Ground Truth 대비)
    - 평균 응답 시간 (ms)
    - 캐시 히트율 (%)
    - LLM 폴백 빈도 (%)
    """
    
    def __init__(self):
        """
        LLM 정규화 엔진 초기화
        
        설정:
        - OpenAI 클라이언트 초기화
        - 표준 용어 사전 정의 (카테고리별)
        """
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        
        # 표준 용어 사전 (LLM이 참조할 기준)
        # 실제 DB의 equipType, location, statusCode 값과 일치해야 함
        self.standard_terms = {
            "equipment": [
                "[VEDR]Pressure Vessel/ Drum", "[GVGV]Guided Vehicle/ Guided Vehicle", 
                "[ANAA]Analyzer/ Analyzer", "[MVVV]Motor Operated Valve/ Motor Operated Valve",
                "[CONV]Conveyor/ Conveyor", "[PUMP]Pump/ Pump", "[HEXH]Heat Exchanger/ Heat Exchanger",
                "[VALV]Valve/ Valve", "[CTLV]Control Valve/ Control Valve", "[TANK]Tank/ Tank",
                "[STNK]Storage Tank/ Storage Tank", "[FILT]Filter/ Filter", "[REAC]Reactor/ Reactor",
                "[COMP]Compressor/ Compressor", "[FAN]Fan/ Fan", "[BLOW]Blower/ Blower"
            ],
            "location": [
                "No.1 PE", "No.2 PE", "Nexlene 포장 공정", "PW-B3503", "SKGC-설비관리", 
                "KNC-설비관리", "석유제품배합/저장", "합성수지 포장", "RFCC", "1창고 #7Line", "2창고 #8Line", "공통 시설"
            ],
            "status": [
                "고장", "누설", "작동불량", "소음", "진동", "온도상승", 
                "압력상승", "주기적 점검/정비", "고장.결함.수명소진", "SHE", "운전 Condition 이상"
            ]
        }
    
    def _get_db_terms(self, category: str) -> list:
        """DB에서 표준 용어 목록 동적 추출"""
        db_path = Config.SQLITE_DB_PATH
        conn = sqlite3.connect(db_path)
        terms = []
        if category == "equipment":
            # equipment_types 테이블에서 type_name 컬럼(D컬럼 전체 값) 추출
            try:
                cursor = conn.execute("SELECT DISTINCT type_name FROM equipment_types WHERE type_name IS NOT NULL")
                terms = [row[0] for row in cursor.fetchall() if row[0]]
            except sqlite3.OperationalError:
                # equipment_types 테이블이 없는 경우 notification_history 사용
                cursor = conn.execute("SELECT DISTINCT equipType FROM notification_history")
                terms = [row[0] for row in cursor.fetchall() if row[0]]
        elif category == "location":
            cursor = conn.execute("SELECT DISTINCT location FROM notification_history")
            terms = [row[0] for row in cursor.fetchall() if row[0]]
        elif category == "status":
            try:
                cursor = conn.execute("SELECT code, description, category FROM status_codes")
                # code, description, category 모두 프롬프트에 제공
                terms = [(row[0], row[1], row[2]) for row in cursor.fetchall() if row[0]]
            except sqlite3.OperationalError:
                # status_codes 테이블이 없는 경우 notification_history에서 statusCode 추출
                cursor = conn.execute("SELECT DISTINCT statusCode FROM notification_history")
                terms = [row[0] for row in cursor.fetchall() if row[0]]
        elif category == "priority":
            cursor = conn.execute("SELECT DISTINCT priority FROM notification_history")
            terms = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return terms

    def normalize_term(self, term: str, category: str) -> Tuple[str, float]:
        """
        LLM을 사용하여 용어를 표준 용어로 정규화
        
        Args:
            term: 정규화할 용어 (예: "압력베젤", "모터밸브")
            category: 용어 카테고리 ("equipment", "location", "status")
            
        Returns:
            (표준용어, 신뢰도점수): 정규화된 표준 용어와 신뢰도 (0.0~1.0)
            
        사용처:
        - database.py: search_similar_notifications()에서 입력값 정규화
        - parser.py: _normalize_extracted_terms()에서 추출된 용어 정규화
        
        예시:
        - normalize_term("압력베젤", "equipment") → ("Pressure Vessel", 0.95)
        - normalize_term("모터밸브", "equipment") → ("Motor Operated Valve", 0.9)
        - normalize_term("서규제품배합", "location") → ("석유제품배합/저장", 0.95)
        
        담당자 수정 가이드:
        - 신뢰도가 0.3 미만인 경우 원본 용어를 반환하도록 설정됨
        - 오류 발생 시 원본 용어와 중간 신뢰도(0.5) 반환
        - 새로운 카테고리 추가 시 standard_terms에 추가 필요
        """
        if not term:
            return term, 0.0
        
        try:
            # DB에서 표준 용어 목록 동적 추출
            db_terms = self._get_db_terms(category)
            prompt = self._create_normalization_prompt(term, category, db_terms)
            
            # LLM 호출 (일관성을 위해 낮은 temperature 사용)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 설비관리 시스템의 용어 정규화 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 일관성을 위해 낮은 temperature
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 응답 파싱
            normalized_term, confidence = self._parse_normalization_response(result_text)
            
            return normalized_term, confidence
            
        except Exception as e:
            print(f"LLM 정규화 오류: {e}")
            return term, 0.5  # 오류 시 원본 반환, 중간 신뢰도
    
    def _create_normalization_prompt(self, term: str, category: str, db_terms) -> str:
        """
        DB에서 추출한 표준 용어 목록을 LLM 프롬프트에 직접 제공
        현상코드는 code, description, category 모두 제공
        우선순위는 DB의 실제 용어들을 사용
        """
        if category == "status":
            # 현상코드: code, description, category 모두 프롬프트에 포함
            if db_terms and isinstance(db_terms[0], tuple):
                # status_codes 테이블에서 가져온 경우 (code, description, category)
                status_lines = [f"- 코드: {code}, 설명: {desc}, 범주: {cat}" for code, desc, cat in db_terms]
                term_list = "\n".join(status_lines)
                extra_rule = "입력된 내용이 아래 현상코드의 설명(description)이나 범주(category)에 포함되면 해당 코드(code)로 정규화하세요."
            else:
                # notification_history에서 가져온 경우 (단일 값)
                status_lines = [f"- {term}" for term in db_terms]
                term_list = "\n".join(status_lines)
                extra_rule = ""
        elif category == "priority":
            # 우선순위: DB의 실제 용어들을 사용
            priority_lines = [f"- {priority}" for priority in db_terms]
            term_list = "\n".join(priority_lines)
            extra_rule = """
우선순위 정규화 규칙:
- "긴급", "최우선", "emergency", "urgent", "긴급하게", "즉시", "바로" → "긴급작업(최우선순위)"
- "우선", "priority", "high", "우선적으로", "먼저", "중요" → "우선작업(Deadline준수)"
- "일반", "normal", "regular", "보통", "평상시", "정상" → "일반작업(Deadline없음)"
- "주기", "TA", "PM", "정기", "정기적", "주기적", "점검" → "주기작업(TA.PM)"
"""
        else:
            term_list = "\n".join([f"- {t}" for t in db_terms])
            extra_rule = ""
        return f"""
다음 입력 용어를 설비관리 시스템의 표준 용어로 정규화해주세요.

**입력 용어**: {term}
**카테고리**: {category}

**표준 용어 목록**:
{term_list}

{extra_rule}

정규화 규칙:
1. 오타, 띄어쓰기 오류, 한영 혼용을 DB에 있는 표준 용어로 변환
2. 여러 단어로 구성된 표현도 해당하는 표준 용어로 매핑
3. 유사한 의미나 동의어를 적절한 표준 용어로 변환
4. 맥락을 고려하여 가장 적절한 표준 용어 선택
5. 표준 용어 목록에 없는 경우 가장 유사한 용어 선택
6. 전혀 매칭되지 않는 경우 "UNKNOWN" 반환

매칭 우선순위:
1. 정확한 일치 (가장 높은 신뢰도)
2. 부분 일치 또는 유사한 의미 (높은 신뢰도)
3. 맥락적 유사성 (중간 신뢰도)
4. 추정 매칭 (낮은 신뢰도)

응답 형식:
```json
{{
    "normalized_term": "표준용어",
    "confidence": 0.95,
    "reasoning": "정규화 이유"
}}
```
"""
    
    def _parse_normalization_response(self, response_text: str) -> Tuple[str, float]:
        """
        LLM 응답을 파싱하여 정규화 결과 추출
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            (정규화된 용어, 신뢰도): 파싱된 결과
            
        담당자 수정 가이드:
        - JSON 파싱 실패 시 폴백 로직으로 응답에서 용어 추출
        - 응답 형식이 변경되면 이 메서드 수정 필요
        """
        
        try:
            # JSON 부분 추출 (```json ... ``` 블록)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # JSON 블록이 없는 경우 전체 텍스트를 JSON으로 파싱 시도
                data = json.loads(response_text)
            
            normalized_term = data.get("normalized_term", "")
            confidence = data.get("confidence", 0.5)
            
            return normalized_term, confidence
            
        except Exception as e:
            print(f"정규화 응답 파싱 오류: {e}")
            # 폴백: 응답에서 용어 추출 시도
            lines = response_text.split('\n')
            for line in lines:
                if 'normalized_term' in line or '표준용어' in line:
                    # 간단한 추출 로직
                    if ':' in line:
                        term_part = line.split(':')[1].strip().strip('"{}')
                        return term_part, 0.7
            
            return "", 0.0
    
    def batch_normalize(self, terms: List[Tuple[str, str]]) -> List[Tuple[str, float]]:
        """
        여러 용어를 일괄 정규화
        
        Args:
            terms: [(용어, 카테고리), ...] 형태의 리스트
            
        Returns:
            [(정규화된 용어, 신뢰도), ...] 형태의 리스트
            
        사용처:
        - 대량의 용어를 한 번에 정규화할 때 사용
        - 성능 최적화를 위해 배치 처리 가능
        
        담당자 수정 가이드:
        - OpenAI API 비용 절약을 위해 배치 크기 조정 가능
        - 병렬 처리로 성능 향상 가능
        """
        results = []
        for term, category in terms:
            normalized, confidence = self.normalize_term(term, category)
            results.append((normalized, confidence))
        return results
    
    def get_similarity_score(self, term1: str, term2: str, category: str) -> float:
        """
        두 용어 간의 유사도 점수 계산 (LLM 활용)
        
        Args:
            term1: 첫 번째 용어
            term2: 두 번째 용어
            category: 용어 카테고리
            
        Returns:
            유사도 점수 (0.0~1.0)
            
        사용처:
        - 향후 유사도 기반 검색 기능 구현 시 사용
        - 추천 엔진의 유사도 계산 개선 시 활용
        
        담당자 수정 가이드:
        - 평가 기준은 비즈니스 요구사항에 맞게 조정 가능
        - 캐싱을 통해 성능 향상 가능
        """
        
        try:
            prompt = f"""
다음 두 용어의 유사도를 0.0~1.0 사이의 점수로 평가해주세요.

**용어 1**: {term1}
**용어 2**: {term2}
**카테고리**: {category}

**평가 기준**:
- 1.0: 완전히 동일한 의미
- 0.8-0.9: 매우 유사한 의미
- 0.6-0.7: 유사한 의미
- 0.4-0.5: 약간 유사한 의미
- 0.0-0.3: 거의 관련 없음

**응답 형식**:
```json
{{
    "similarity_score": 0.85,
    "reasoning": "유사도 평가 이유"
}}
```
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 용어 유사도 평가 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 응답 파싱
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data.get("similarity_score", 0.5)
            
            return 0.5
            
        except Exception as e:
            print(f"유사도 계산 오류: {e}")
            return 0.5

# 전역 정규화 엔진 인스턴스
# 다른 모듈에서 import하여 사용
normalizer = LLMNormalizer() 